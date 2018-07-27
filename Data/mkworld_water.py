"""
Usage:

   mkworld_water.py -I configfile

Steps:

Preperation
~~~~~~~~~~~
- in the first step the script take one or multiple polygons
  to cut-out parts of the planet file (made using use ogr2poly.py to convert to osm poly)
- make ini files for osm2hydro for each polygon. The filenames
  should have the same name but a .ini extension

Running
~~~~~~~
- obtain a planet.osm file (use pbf or o5m format if possible)

Run the script:
- in the second step te splitter program us used to split the pbf in tiles
  for each polygon,
- next the osm2hydro program is run for each time
- finally the tiles are merged using gdal_merge 


Runtime (on a 6 core Mac Pro 3.33 Ghz)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Breaking up of the planet file in areas: +- 3hrs
# Splitting-up the areas in small tiles using splitter: +-4hr
# Running osm2hydro on all tiles +- 16hr
# merging tiles into makes for the world +- 45min


Requirements
~~~~~~~~~~~~
- Make sure the number of open fils can be higher than 1024

"""

import ConfigParser, sys, os, getopt
import time, subprocess, shlex


def removeFinishedProcesses(processes):
    """ given a list of (commandString, process),
        remove those that have completed and return the result
    """
    newProcs = []
    for pollCmd, pollProc in processes:
        retCode = pollProc.poll()
        if retCode == None:
            # still running
            newProcs.append((pollCmd, pollProc))
        elif retCode != 0:
            # failed
            raise Exception("Command %s failed" % pollCmd)
        else:
            print "Command %s completed successfully" % pollCmd
    return newProcs


def runCommands(commands, maxCpu):
    """
    Runs a list of processes deviding
    over maxCpu
    """
    processes = []
    for command in commands:
        command = command.replace('\\', '/')  # otherwise shlex.split removes all path separators
        print command
        proc = subprocess.Popen(shlex.split(command))
        procTuple = (command, proc)
        processes.append(procTuple)
        while len(processes) >= maxCpu:
            time.sleep(.2)
            processes = removeFinishedProcesses(processes)

    # wait for all processes
    while len(processes) > 0:
        time.sleep(0.5)
        processes = removeFinishedProcesses(processes)
    print "All processes (" + str(len(commands)) + ") completed."


def configset(config, section, var, value, overwrite=False):
    """   
    Sets a string in the in memory representation of the config object
    Deos NOT overwrite existing values if overwrite is set to False (default)
    
    Input:
        - config - python ConfigParser object
        - section - section in the file
        - var - variable (key) to set
        - value - the value to set
        - overwrite (optional, default is False)
   
    Returns:
        - nothing
        
    """

    if not config.has_section(section):
        config.add_section(section)
        config.set(section, var, value)
    else:
        if not config.has_option(section, var):
            config.set(section, var, value)
        else:
            if overwrite:
                config.set(section, var, value)


def iniFileSetUp(configfile):
    """
    Reads .ini file and sets default values if not present
    """

    # setTheEnv(runId='runId,caseName='caseName)
    # Try and read config file and set default options
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(configfile)
    return config


def configget(log, config, section, var, default):
    """

    Gets a string from a config file (.ini) and returns a default value if
    the key is not found. If the key is not found it also sets the value
    with the default in the config-file

    Input:
        - config - python ConfigParser object
        - section - section in the file
        - var - variable (key) to get
        - default - default string

    Returns:
        - string - either the value from the config file or the default value
    """

    Def = False
    try:
        ret = config.get(section, var)
    except:
        Def = True
        ret = default
        # log.info( "returning default (" + default + ") for " + section + ":" + var)
        configset(config, section, var, default, overwrite=False)

    default = Def
    return ret


def run_splitter(osmfile, boundary, outputdir, startnumber=1, predareas=None,
                 splitter="/home/schelle/src/osm2hydro/third-party/splitter/splitter.jar",
                 java="c:\Windows\System32\java.exe"):
    """
    Calls splitter to break-up the planet
    - boundary - osmpoly file (make with ogr2poly)
    - predareas - areas.list file from previous run
    """
    # Should be put in the python sccript
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    if predareas:
        print "Pre-defined areas"
        ret = os.system(
            java + " -Xmx12000m -jar " + splitter + "  --split-file=" + predareas + " --output-dir=" + outputdir + " --description=\"OSM World splitter results\" --keep-complete=true --mapid=" + str(
                startnumber) + " --output=pbf  --polygon-file=" + boundary + " --write-kml=areas.kml " + osmfile)
        # ret = os.system(java + " -Xmx8000m -jar " + splitter + "  --split-file=" + predareas + " --output-dir=" + outputdir + " --description=\"OSM World splitter results\" --keep-complete=true --mapid=" + str(startnumber) + " --output=pbf  --polygon-file=" +boundary+ " --write-kml=areas.kml " + osmfile)
        # print(java + " -Xmx8000m -jar " + splitter + "  --split-file=" + predareas + " --output-dir=" + outputdir + " --description=\"OSM World splitter results\" --keep-complete=true --mapid=" + str(startnumber) + " --output=pbf  --polygon-file=" +boundary+ " --write-kml=areas.kml " + osmfile)
    else:
        ret = os.system(
            java + " -Xmx12000m -jar  " + splitter + " --overlap=3000  --output-dir=" + outputdir + " --description=\"OSM World splitter results\" --keep-complete=true --mapid=" + str(
                startnumber) + " --output=pbf  --polygon-file=" + boundary + " --write-kml=areas.kml " + osmfile)
        # ret = os.system(java + " -Xmx8000m -jar  " + splitter + " --output-dir=" + outputdir + " --description=\"OSM World splitter results\"  --mapid=" + str(startnumber) + " --output=pbf  --polygon-file=" +boundary+ " --write-kml=areas.kml " + osmfile)
        # print(java + " -Xmx8000m -jar  " + splitter + " --output-dir=" + outputdir + " --description=\"OSM World splitter results\"  --mapid=" + str(startnumber) + " --output=pbf  --polygon-file=" +boundary+ " --write-kml=areas.kml " + osmfile)

    if ret:
        print "Error, command returned non zero exit code:" + str(ret)


def read_splitter_areas(fname):
    """
    reads a splitter .list file with tile min max
    returns list of lists:
        tilename,ymin,xmin,ymax,xmax
        
    Example file:
    -------------
    # List of areas
    # Generated Thu Nov 07 15:12:37 CET 2013
    #
    00000001: -1933312,5134336 to -538624,5818368
    #       : -41.484375,110.170898 to -11.557617,124.848633
    
    00000002: -985088,5818368 to -387072,7188480
    #       : -21.137695,124.848633 to -8.305664,154.248047
    00000281: 2396160,337920 to 2430976,362496
    #       : 51.416016,7.250977 to 52.163086,7.778320
    """

    def my_split(s, seps):
        res = [s]
        for sep in seps:
            s, res = res, []
            for seq in s:
                res += seq.split(sep)
        return res

    ret = []
    fs = open(fname, 'r')
    # Convert the splitter map units back to decimal degree
    corconv = 360.0 / 2.0 ** 24.0
    # convdev = round(((1 << 24) / 360.0),6)
    # Unfortunately this is neede in soem cases .....
    overlap = 0.008333333333 * 0.5

    for line in fs:
        if '#' not in line:
            zz = my_split(line.strip(), [':', ',', ' to '])
            if len(zz) == 5:
                new = []
                for it in zz:
                    new.append(it.strip())
                new = []
                new.append(zz[0])
                nr = 0
                for it in zz[1:len(zz)]:
                    nr = nr + 1
                    if nr == 1:
                        new.append(round(int(it) * corconv - overlap, 6))
                    if nr == 2:
                        new.append(round(int(it) * corconv - overlap, 6))
                    if nr == 3:
                        new.append(round(int(it) * corconv + overlap, 6))
                    if nr == 4:
                        new.append(round(int(it) * corconv + overlap, 6))

                ret.append(new)
    fs.close()
    return ret


def usage(*args):
    sys.stdout = sys.stderr
    for msg in args: print msg
    print __doc__
    sys.exit(0)


def mergetiles(thedir, regions, odir="./", prefix="world"):
    """
    Simple script to merge the tiles into single maps using gdal_merge
    """

    import glob
    import fnmatch
    import os

    # regions=["11.poly","10.poly","9.poly","8.poly","7.poly","6.poly","5.poly","4.poly","3.poly","2.poly","1.poly"]


    matches = []

    patterns = ["lu_buildings.tif", "roads_den.tif", "lu_paved.tif", "lu_pavedpol.tif", "lu_water.tif",
                "lu_unpaved.tif", "lu_roads.tif"]

    def getflist(subdir, pattern):
        for dirName, subdirList, fileList in os.walk(subdir):
            for filename in fnmatch.filter(fileList, pattern):
                matches.append(os.path.join(dirName, filename))
        return matches

    print thedir
    for pattern in patterns:
        matches = []
        for region in regions:
            matches = getflist(os.path.join(thedir, region), pattern)
            a = "\n"
            inflist = a.join(matches)

        fp = open('flist.txt', 'w')
        fp.write(inflist)
        fp.close()
        ofile = os.path.join(odir, pattern)
        mergestr = "gdal_merge.py -n 0 -o " + ofile + " --optfile flist.txt"
        if os.path.exists(ofile):
            print "Skipping :" + ofile
        else:
            print mergestr
            os.system(mergestr)
            os.remove('flist.txt')
            os.system("pigz -v -p6 " + ofile)
            # os.system("cp " + ofile + ".gz "  + os.path.join("/home/jaap/Dropbox",pattern + ".gz"))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
        if len(argv) == 0:
            usage()
            return

    opts, args = getopt.getopt(sys.argv[1:], 'I:')
    configfile = "planet.ini"
    boundaries = []

    maxCPU = 3  # For osmconvert

    for o, a in opts:
        print o, a
        if o == '-I': configfile = a

    config = iniFileSetUp(configfile)

    java = configget(None, config, "osmworld", "java", "c:\Windows\System32\java.exe")
    maxCPU = int(configget(None, config, "osmworld", "maxCPU", str(maxCPU)))
    outputdir = configget(None, config, "osmworld", "outputdir", "world")

    if not os.path.exists(outputdir):
        print "Making outputdir: " + outputdir
        os.makedirs(outputdir)

    osmfile = configget(None, config, "osmworld", "osmfile", "planet.o5m")
    osmcutdir = configget(None, config, "osmworld", "osmcutdir", ".")
    splitter = configget(None, config, "osmworld", "splitter", "splitter.jar")
    _boundaries = configget(None, config, "osmworld", "boundaries",
                            '["area_0.poly","area_1.poly","area_2.poly","area_3.poly","area_4.poly","area_5.poly","area_6.poly"]')
    exec "boundaries = " + _boundaries
    osmconvert = configget(None, config, "osmworld", "osmconvert", "..\..\dist\win32\osmconvert.exe")
    osm2hydro = configget(None, config, "osmworld", "osm2hydro", "python ..\osm2hydro\osm2hydro_metres.py")

    # splitworld = int(configget(None,config,"osmworld","splitworld", "1"))
    splitworld = 1
    deleteshapes = 0
    mergetiles = 0
    # Set temp dir for gdal_density (for the hires files)
    os.environ["GDAL_DENSITY_TMP"] = configget(None, config, "osmworld", "tmpdir", "./")

    # Main loop
    # ----------------------------------
    start = 1  # to keep track of the number of tiles between splitter runs
    commands = []
    # Loop over all regions (define by the boundary polygons)

    # STEP 1: Split the planet into regions with each a seperate ini file
    if splitworld:
        for poly in boundaries:
            # Use osmconvert to cut out a pbf for the polygon if is not already esists
            thisodir = outputdir + "_" + poly
            if not os.path.exists(osmcutdir + "/" + poly + ".pbf"):
                print "Cutting " + osmfile + " using polygon : " + poly
                execstr = osmconvert + " " + osmfile + " -o=" + osmcutdir + "/" + poly + ".pbf -B=" + poly + " -v  --out-pbf --hash-memory=1000 --drop-broken-refs  --drop-version --drop-relations --complex-ways --complete-ways --drop-author"
                commands.append(execstr)
                # ret = os.system(execstr)

            else:
                print "Skipping extracting polygon cutout from planet: " + poly + ".pbf"

        runCommands(commands, maxCPU)

    # STEP 2: Run splitter on each of the regions
    for poly in boundaries:
        thisodir = outputdir + "/" + poly
        # Run the splitter program for this polygon. This will split it up in smaller tiles
        if not os.path.exists(os.path.join(thisodir, "areas.list")):
            print "Splitting and calculating list..."
            run_splitter(osmcutdir + "/" + poly + ".pbf", poly, thisodir, startnumber=start, predareas=None, java=java,
                         splitter=splitter)

        else:
            if not os.path.exists(os.path.join(thisodir, "00000001.osm.pbf")):
                print "Splitting from existing list..."
                run_splitter(osmcutdir + "/" + poly + ".pbf", poly, thisodir, startnumber=start,
                             predareas=os.path.join(thisodir, "areas.list"), java=java, splitter=splitter)
            print "Skipping splitting of file: " + poly + ".pbf"

    # STEP 3: Run osm2hydro on each tile for each region
    for poly in boundaries:
        commands = []
        delcommands = []

        thisodir = outputdir + "/" + poly
        # now run OSM2hydro for each tile
        # Reaad the tile parameters from the areas.list file generated by splitter
        res = read_splitter_areas(os.path.join(thisodir, "areas.list"))
        start = int(res[-1][0]) + 1
        print "Last tile number: " + str(start)
        osm2ini = "osm2tiff.ini"
        # Now loop for all tiles
        for tile in res:
            tilefile = tile[0]
            if not os.path.exists(os.path.join(thisodir, str(tilefile), "OMS2Hydro.log")):
                ymin = tile[1]
                xmin = tile[2]
                ymax = tile[3]
                xmax = tile[4]
                # This was for liux
                #osm2hydrostr = osm2hydro + " -N " + tilefile + " -C " + thisodir + " -c " + osm2ini + "  -E \'[" + str(
                osm2hydrostr = osm2hydro + " -c " + osm2ini + " -O  " + thisodir + "/" + str( tilefile) + ".osm.pbf -o " + thisodir +"/" + str(tilefile)
                # This for windows
                # osm2hydrostr = osm2hydro + " -N " + tilefile + " -C " + thisodir+ " -c " + osm2ini + "  -E [" + str(xmin) +"," + str(ymin) + "," + str(xmax) + "," + str(ymax) +"] -O  " + thisodir+   "/" + str(tilefile) + ".osm.pbf"
                commands.append(osm2hydrostr)
                deletecmd = "rm -f " + os.path.join(thisodir, str(tilefile), "osmshapes/*")
                delcommands.append(deletecmd)

            else:
                print "Skipping osm2hydro for tile: " + str(tile)

        runCommands(commands, maxCPU)
        if deleteshapes:
            runCommands(delcommands, maxCPU)

    # Finally merge the lot        
    if mergetiles:
    	mergetiles(outputdir, boundaries, odir=configget(None, config, "osmworld", "finaloutputdir", "./"),
               prefix=os.path.basename(osmfile))


if __name__ == "__main__":
    main()
