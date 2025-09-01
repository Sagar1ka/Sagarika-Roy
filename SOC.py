# -*- coding: utf-8 -*-
# Google Earth Engine (Python API) version of your JS code

import ee
ee.Initialize()  # Make sure you are authenticated before running

#----------------------------------------- PARAMETERS ------------------------------------------#
stardate = '2018-01-01'
enddate  = '2019-12-31'
Data_Scale = 50

# -------------------------------------- PLACEHOLDERS ------------------------------------------#
# TODO: define your study area and 2018 mosaic
# Example:
# studyarea = ee.FeatureCollection('users/you/your_study_area').geometry()
# Mosaico_2018 = ee.Image('users/you/Mosaic_2018_asset')
studyarea = ee.Geometry.Polygon([[
    [ -72.5, -12.0 ],
    [ -72.5, -13.0 ],
    [ -71.5, -13.0 ],
    [ -71.5, -12.0 ]
]])  # <-- REPLACE with your geometry
Mosaico_2018 = ee.Image('users/you/Mosaic_2018_asset')  # <-- REPLACE

#------------------------------------------- COLLECTIONS ---------------------------------------#
SRTM              = ee.Image('USGS/SRTMGL1_003')  # 30m
COPERNICUS_S1     = ee.ImageCollection('COPERNICUS/S1_GRD')
Temperature8d     = ee.ImageCollection('MODIS/006/MOD11A2')  # 1km, 8-day
Temperature1d     = ee.ImageCollection('MODIS/006/MOD11A1')  # 1km, daily
Precipitation_1d  = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
Relative_humidity = ee.ImageCollection('NOAA/GFS0P25')

#----------------------------------------- EXTERNAL DATA ---------------------------------------#
Forest_Mask = ee.Image('users/leofabiop120/Suelo/Mask_Bosque')

#--------------------------------------- LANDSAT INDEXES ---------------------------------------#
# In JS you used an external module:
#    var addIndex = require("users/leofabiop120/SUELO:addIndices_Landsat");
# Python API does not support require(). If you need those indices, either:
#  (a) copy the index formulas here, or
#  (b) precompute them and load as an Image.
Mosaic_2018_mask = Mosaico_2018.updateMask(Forest_Mask)

# === Example: compute a subset of common indices directly (NDVI, EVI, etc.)
# Adjust band names to your mosaic (often: 'B2','B3','B4','B5','B6','B7' for Landsat 8/9;
# here I assume common reflectance bands named 'blue','green','red','nir','swir1','swir2')
def add_indices(img):
    blue  = img.select('blue')
    green = img.select('green')
    red   = img.select('red')
    nir   = img.select('nir')
    sw1   = img.select('swir1')
    sw2   = img.select('swir2')
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    evi  = nir.subtract(red).multiply(2.5).divide(
        nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1.0)).rename('EVI')
    savi = nir.subtract(red).multiply(1.5).divide(nir.add(red).add(0.5)).rename('SAVI')
    bsi  = (sw1.add(red).subtract(nir.add(blue))).divide(
        sw1.add(red).add(nir).add(blue)).rename('BSI')
    gndvi = nir.subtract(green).divide(nir.add(green)).rename('GNDVI')
    nirv  = ndvi.multiply(nir).rename('NIRv')
    # Keep originals for convenience
    return img.addBands([ndvi, evi, savi, bsi, gndvi, nirv])

mosaic_2018_index = add_indices(Mosaic_2018_mask)

Spectral_Index_Databases = mosaic_2018_index.select([
    'NDVI','EVI','SAVI','BSI','NIRv','GNDVI','blue','green','red','nir','swir1','swir2'
])

#--------------------------------------- TOPOGRAPHIC DATA --------------------------------------#
# In JS you used TAGEE module functions. Python cannot require that module.
# We’ll compute basic terrain attributes with EE built-ins and reproduce your TWI.

bbox = studyarea

# Water mask from Hansen (as in your code)
hansen_2016 = ee.Image('UMD/hansen/global_forest_change_2016_v1_4').select('datamask')
hansen_2016_wbodies = hansen_2016.neq(1).eq(0)
waterMask = hansen_2016.updateMask(hansen_2016_wbodies)

# DEM
demSRTM = ee.Image('USGS/SRTMGL1_003').clip(bbox).mask(Forest_Mask).rename('DEM')

# Gaussian smoothing
gaussian_kernel = ee.Kernel.gaussian(radius=3, sigma=2, units='pixels', normalize=True)
demSRTM_smooth = demSRTM.convolve(gaussian_kernel).resample('bilinear')

# Terrain analysis (using EE terrain)
terrain = ee.Terrain.products(demSRTM_smooth)  # elevation, slope, aspect, etc.
# Make sure to apply water mask similar to JS
terrain_masked = terrain.updateMask(waterMask)

elevation = terrain_masked.select('elevation').rename('Elevation')
slope     = terrain_masked.select('slope').rename('Slope')
aspect    = terrain_masked.select('aspect').rename('Aspect')

# TWI
dem_hs  = ee.Image('WWF/HydroSHEDS/03VFDEM')
flowacc = ee.Image('WWF/HydroSHEDS/15ACC')

slope_deg  = ee.Terrain.slope(dem_hs).clip(studyarea).mask(Forest_Mask)
# TWI formula from your code
twi = (flowacc.multiply(ee.Image(flowacc.projection().nominalScale())
        .divide(slope_deg.multiply(ee.Image(3.141592653589793)).divide(ee.Image(180)).tan()))
       ).log().rename('TWI')
twi = twi.clip(studyarea).mask(Forest_Mask)

Topographic_Database = elevation.addBands([slope, aspect, twi]).updateMask(Forest_Mask)

#----------------------------------------- CLIMATE DATA ----------------------------------------#
# Kelvin -> Celsius for MOD11A1
def KtoC(image):
    y = image.select('LST_Day_1km')
    x = y.expression('banda * 0.02 - 273.15', {'banda': y}).rename('Temp_C')
    return x.copyProperties(image, ['system:time_start', 'system:time_end'])

def fechaLugar(imagecollection):
    return imagecollection.filterDate(stardate, enddate)

# MODIS cloud mask (if needed later)
def maskClouds(image):
    QA = image.select('state_1km')
    bitMask = 1 << 10
    return image.updateMask(QA.bitwiseAnd(bitMask).eq(0))

# Water mask using QA (if needed later)
def water(image):
    qa = image.select('state_1km')
    mask = (qa.bitwiseAnd(1 << 3).eq(0)
            .And(qa.bitwiseAnd(1 << 4).eq(0))
            .And(qa.bitwiseAnd(1 << 5).eq(0)))
    return image.updateMask(mask)

def PREC(image):
    return image.select('precipitation').rename('Precipitacion')

def HuRe(image):
    return image.select('relative_humidity_2m_above_ground').rename('RH')

def statistics(imageCollection):
    # get first band name
    first_band = ee.String(ee.List(imageCollection.first().bandNames()).get(0))
    mean_img = imageCollection.mean().rename(first_band.cat('mean'))
    return mean_img.clip(studyarea).updateMask(Forest_Mask)

# Temperature statistics (2000-01-01 to 2018-01-01, daily)
temperature_filter = Temperature1d.filterDate('2000-01-01', '2018-01-01').map(KtoC)
temperature_statistics = statistics(temperature_filter)

# Precipitation statistics
prec_filter = Precipitation_1d.filterDate('2000-01-01', '2018-01-01').map(PREC)
prec_statistics = statistics(prec_filter)

# Relative humidity at a specific creation time (mirroring your filter)
# NOTE: The exact filter you used may return nothing today; adjust as needed.
RH = Relative_humidity.filter(
    ee.Filter.eq('creation_time',
                 ee.Date(0).update(2020, 12, 30, 6, 0, 0).millis())
).map(HuRe)
RH_statistics = statistics(RH)

Climate_databases = temperature_statistics.addBands([prec_statistics, RH_statistics])

#----------------------------------- MODEL INPUT STACK -----------------------------------------#
# Model A: topo + climate + spectral indices
stack = Topographic_Database.addBands(Climate_databases).addBands(Spectral_Index_Databases)

predictionBands = stack.bandNames()

#------------------------------------ TRAINING DATA --------------------------------------------#
classFeatures = ee.FeatureCollection('users/leofabiop120/Suelo/268_pts_INF')
Column_Name = 'SOC_TCH'

# Optionally buffer samples (commented out in your JS)
# def buffer_feature(f):
#     return f.buffer(50, 5)
# classFeatures = classFeatures.map(buffer_feature)

trainingSamples = stack.sampleRegions(
    collection=classFeatures,
    properties=[Column_Name],
    scale=Data_Scale,
    tileScale=16,
    geometries=True
)

#---------------------------------- RANDOM FOREST (GLOBAL) -------------------------------------#
classifier_RF = (ee.Classifier.smileRandomForest(100)
                 .setOutputMode('REGRESSION')
                 .train(trainingSamples, Column_Name, predictionBands))

Carbon_Soil_RF = stack.classify(classifier_RF).rename('Carbon_Soil_RF')

#----------------------------------------- RMSE / R² -------------------------------------------#
trained_samples = stack.sampleRegions(
    collection=classFeatures,
    properties=[Column_Name],
    scale=Data_Scale,
    tileScale=16,
    geometries=True
)

proportion = 0.7
muestrasR = trained_samples.randomColumn()
training = muestrasR.filter(ee.Filter.lt('random', proportion))
testing  = muestrasR.filter(ee.Filter.gte('random', proportion))

classifier_ent_RF = (ee.Classifier.smileRandomForest(100)
                     .setOutputMode('REGRESSION')
                     .train(training, Column_Name, predictionBands))
classified_pred_RF = stack.classify(classifier_ent_RF).rename('class_pred')

validation_RF = classified_pred_RF.sampleRegions(
    collection=training,
    scale=Data_Scale,
    tileScale=16,
    geometries=True
)

val_extracted_RF = validation_RF.reduceColumns(
    reducer=ee.Reducer.toList(2),
    selectors=[Column_Name, 'class_pred']
).get('list')

# Compute RMSE and R²
val_array = ee.Array(val_extracted_RF)
obs1  = val_array.transpose().slice(0, 0, 1).project([1])
pred1 = val_array.transpose().slice(0, 1, 2).project([1])

rmse1 = obs1.subtract(pred1).pow(2).reduce('mean', [0]).sqrt()
r2_RF = ee.Number(
    validation_RF.reduceColumns(ee.Reducer.pearsonsCorrelation(),
                                [Column_Name, 'class_pred']).get('correlation')
).pow(2)

print('RMSE: Random Forest =', rmse1.getInfo())
print('R²:   Random Forest =', r2_RF.getInfo())

#-------------------------------- VARIABLE IMPORTANCE (small model) -----------------------------#
classifier_test = (ee.Classifier.smileRandomForest(5)
                   .setOutputMode('REGRESSION')
                   .train(training, Column_Name, predictionBands))
explain_dict = classifier_test.explain().getInfo()
importance = explain_dict.get('importance', {})
print('Variable importance:', importance)

#--------------------------- ENSEMBLE STD. DEVIATION (UNCERTAINTY) ------------------------------#
def train_with_seed(seed):
    clf = ee.Classifier.smileRandomForest(numberOfTrees=5, seed=seed).setOutputMode('REGRESSION')
    return clf.train(trainingSamples, Column_Name, predictionBands)

seeds = ee.List.sequence(1, 10)
classifiers = seeds.map(lambda s: train_with_seed(ee.Number(s)))

def classify_with(c):
    return stack.classify(ee.Classifier(c))
result_list = classifiers.map(classify_with)

col = ee.ImageCollection(result_list)
collection_std = col.reduce(ee.Reducer.stdDev())
# collection_std is analogous to your 'standard_deviation' layer

#--------------------------------------------- EXPORTS -----------------------------------------#
# Union bands for vector sampling export
union1 = stack.addBands([Carbon_Soil_RF, collection_std])

Datos_RF = union1.reduceRegions(
    collection=classFeatures,
    reducer=ee.Reducer.mean(),
    scale=Data_Scale,
    tileScale=16
)

# --------- Export to ASSET --------- #
ee.batch.Export.table.toAsset(
    collection=Datos_RF,
    description='Data_Soil_RF_Asset'
).start()

ee.batch.Export.image.toAsset(
    image=collection_std,
    description='Standard_Deviation_Asset',
    region=studyarea.bounds(),
    scale=Data_Scale,
    maxPixels=1e13
).start()

ee.batch.Export.image.toAsset(
    image=Carbon_Soil_RF,
    description='Raster_Carbon_Soil_RF_Asset',
    region=studyarea.bounds(),
    scale=Data_Scale,
    maxPixels=1e13
).start()

ee.batch.Export.image.toAsset(
    image=stack,
    description='Stack_variables_Asset',
    region=studyarea.bounds(),
    scale=Data_Scale,
    maxPixels=1e13
).start()

# --------- Export to DRIVE --------- #
ee.batch.Export.table.toDrive(
    collection=Datos_RF,
    description='Data_Soil_RF_Drive',
    fileFormat='CSV'
).start()

ee.batch.Export.image.toDrive(
    image=Carbon_Soil_RF,
    description='Carbon_Soil_Drive_RF_Drive',
    scale=30,
    maxPixels=1e13
).start()

ee.batch.Export.image.toDrive(
    image=stack,
    description='Stack_variables_Drive',
    scale=30,
    maxPixels=1e13
).start()

ee.batch.Export.image.toDrive(
    image=collection_std,
    description='standard_deviation',
    scale=30,
    maxPixels=1e13
).start()
