# Shoudl be put in the python sccript
java -jar ~/src/splitter/dist/splitter.jar  --output-dir=tiles_splitter --description="OSM World splitter results" --keep-complete=true --mapid=1 --output=pbf  --max-nodes=3200000 --polygon-file=oz.poly --write-kml=areas.kml australia-oceania-latest.osm.pbf | tee  splitlog.log

