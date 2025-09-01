Obtaining the spatial distribution information of soil organic carbon (SOC) is significant to quantify the carbon budget and guide land management for migrating carbon emissions. Digital soil mapping of SOC at a regional scale is challenging due to the complex SOC-environment relationships. Vegetation phenology that directly indicates a long time vegetation growth characteristics can be potential environmental covariates for SOC prediction. Deep learning has been developed for soil mapping recently due to its ability of constructing high-level features from the raw data. 

Step 2. Data Collection
•	DEM: SRTM (30m)
•	Climate: MODIS (Temperature), CHIRPS (Precipitation), NOAA/GFS (RH)
•	Radar: Copernicus S1
•	Spectral: Landsat Mosaic (2018)
•	Ancillary: Forest mask, Hansen water bodies
________________________________________
Step 3. Preprocessing
•	Apply Forest mask
•	Clip datasets to study area
•	Cloud masking (MODIS)
•	Convert units (e.g., Kelvin → Celsius)
•	DEM smoothing (Gaussian filter)
________________________________________
Step 4. Feature Extraction
•	Spectral Indices: NDVI, EVI, SAVI, BSI, GNDVI, NIRv, etc.
•	Topographic Variables: Elevation, Slope, Aspect, TWI
•	Climate Variables: Mean Temp (°C), Precipitation, RH
________________________________________
Step 5. Dataset Construction
•	Stack Topographic + Climate + Spectral features → Multiband dataset
________________________________________
Step 6. Training Data
•	Load field samples (SOC measurements)
•	Overlay with stacked dataset → extract pixel values
•	Create training and validation sets (70/30 split)
________________________________________
Step 7. Model Training (Random Forest)
•	Train Random Forest Regressor (100 trees)
•	Input: predictor bands
•	Output: Soil Organic Carbon (SOC) prediction
________________________________________
Step 8. Prediction
•	Apply trained model → generate SOC prediction raster
________________________________________
Step 9. Accuracy Assessment
•	Compute RMSE
•	Compute R²
•	Variable importance analysis
•	Ensemble classification → standard deviation (uncertainty map)
________________________________________
Step 10. Visualization & Export
•	Display maps (SOC raster, uncertainty layer)
•	Export:
o	SOC raster to Asset/Drive
o	Stacked features to Asset/Drive
o	Validation statistics to CSV


