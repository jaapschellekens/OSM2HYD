"""
Simple script to merge the tiles into single maps using gdal_merge
"""

import glob
import fnmatch
import os

#regions=["11.poly","10.poly","9.poly","8.poly","7.poly","6.poly","5.poly","4.poly","3.poly","2.poly","1.poly"]
regions=["10.poly","9.poly","7.poly","6.poly","5.poly","4.poly","3.poly","2.poly","1.poly"]
#regions=["11.poly"]


matches = []

patterns = ["lu_buildings.tif","roads_den.tif","lu_paved.tif","lu_pavedpol.tif","lu_water.tif","lu_unpaved.tif","lu_roads.tif"]



def getflist(subdir,pattern):
    for dirName, subdirList, fileList in os.walk(subdir):
        for filename in fnmatch.filter(fileList, pattern):
            matches.append(os.path.join(dirName,filename))
    return matches


for pattern in patterns:
    matches = []
    for region in regions:
        matches = getflist(region,pattern)
        a = "\n"
        inflist = a.join(matches)

    fp = open('flist.txt','w')
    fp.write(inflist)
    fp.close()
    ofile = "2015_" + region + pattern
    mergestr = "gdal_merge.py -co COMPRESS=LZW -co BIGTIFF=YES -co TILED=TRUE -n 0 -o " + ofile + " --optfile flist.txt"
    if os.path.exists(ofile):
        print "Skipping :" + ofile
    else:
        print mergestr
        os.system(mergestr)
        os.remove('flist.txt')

