import numpy as np
import os, yaml
import datetime as dt
from dateutil.parser import parse
import pandas as pd
import logging

# Plotting
import datetime as dt


import pcse
from pcse.util import WOFOST71SiteDataProvider, WOFOST72SiteDataProvider
from pcse.models import Wofost72_PP, Wofost72_WLP_FD
from pcse.fileinput import YAMLCropDataProvider

from pcse.util import WOFOST72SiteDataProvider, DummySoilDataProvider
from pcse.base import ParameterProvider
from pcse.engine import Engine
from pcse.fileinput.csvweatherdataprovider import CSVWeatherDataProvider


def prepareWeather(in_fname: str):
    """
    Read weather file, after convert to WOFOST CSV format and
    read into memory to PCSE weather Class

    in: in_fname (str) - path to csv file with weather time-series
    """
    # read weather time-series
    weather_df = pd.read_csv(in_fname)
    # future name

    path_to_save_csv_file = os.path.splitext(in_fname)[0] + "_WOFOST.csv"
    # path_to_save_csv_file = './wofost_weather.csv'
    # pattern for WOFOST format
    text = open("./pattern.csv", "r")
    dictReplace = {
        "1111": "37.0",
        "2222": "51.5",
        "3333": "210.05",  # m
        "4444": "0.172729",
        "5555": "0.565318",
    }
    for key, value in dictReplace.items():
        text = "".join([i for i in text]).replace(key, str(value))
    x = open(path_to_save_csv_file, "w")
    x.writelines(text)
    x.close()
    weather_df.to_csv(
        path_to_save_csv_file, mode="a", header=False, index=False, na_rep="NaN"
    )
    weather = CSVWeatherDataProvider(path_to_save_csv_file, force_reload=True)
    
    # os.remove(path_to_save_csv_file)
    return weather


def run_wofost(
    weather,
    sowing_date: str,
    harvesting_date: str,
    crop_end_type: str = "maturity",
    crop_name: str = "sugarbeet",
    crop_variety: str = "Sugarbeet_603",
    models: list = ["FLD", "PP"],
) -> dict:

    """
    Prepare parameters: meteo, agrotechnology and run WOFOST simulation in PP and FLD modes.

    Parameters
    ----------
    crop_name: str
        Crop name fow WOFOST model
    crop_variety: str
        Crop variety fow WOFOST crop
    sowing_date: str
        Date of crop sowing, ex. %Y-%m-%d
    harvest_date: str
    - optional
        Date of crop harvest, ex. %Y-%m-%d

    Returns
    -------
    results: dict
        dict with PCSE objects: cropd, wdp
        if run_similation: True
            return computed default yield
    To-Do
    -----


    Example
    -------

    """
    cropd = YAMLCropDataProvider(
        repository="https://raw.githubusercontent.com/ajwdewit/WOFOST_crop_parameters/master/"
    )
    # Some site parameters
    sited = WOFOST71SiteDataProvider(WAV=50, SMLIM=0.7)

    soild = DummySoilDataProvider()  # Used real soil parameters from kshen

    soild["SMW"] = 0.15
    soild["SMFCF"] = 0.3
    soild["SM0"] = 0.566

    _campaign_start_date_dt = parse(sowing_date) - dt.timedelta(days=5)
    campaign_start_date = dt.datetime.strftime(
        _campaign_start_date_dt, format="%Y-%m-%d"
    )

    max_duration = 300

    # Here we define the agromanagement for crop
    agro_yaml = f"""
    - {campaign_start_date}:
        CropCalendar:
            crop_name: {crop_name}
            variety_name: {crop_variety}
            crop_start_date: {sowing_date}
            crop_start_type: emergence
            crop_end_date: {harvesting_date}
            crop_end_type: {crop_end_type}
            max_duration: {max_duration}
        TimedEvents: null
        StateEvents: null
    """
    """
    """
    agro = yaml.safe_load(agro_yaml)

    firstkey = list(agro[0])[0]
    cropcalendar = agro[0][firstkey]["CropCalendar"]

    cropd.set_active_crop(cropcalendar["crop_name"], cropcalendar["variety_name"])

    params = ParameterProvider(cropdata=cropd, sitedata=sited, soildata=soild)

    defualtCropYield = {}

    modelDict = {"FLD": Wofost72_WLP_FD, "PP": Wofost72_PP}
    for model_type in ["FLD"]:
        params = ParameterProvider(cropdata=cropd, sitedata=sited, soildata=soild)
        model_runner = modelDict[model_type](params, weather, agro)
        model_runner.run_till_terminate()
        r = model_runner.get_output()
        defualtCropYield[model_type] = r
        del model_runner
    del weather
    return defualtCropYield


def getCropCalendar(crop: str, year: str) -> dict:

    dictAgro = {
        "barley": {"plant_day": "2021-04-30", "harvest_day": "2021-09-06"},
        "soybean": {"plant_day": "2021-04-15", "harvest_day": "2021-08-16"},
        "wheat": {"plant_day": "2021-05-18", "harvest_day": "2021-09-01"},
        "sugarbeet": {"plant_day": "2021-04-28", "harvest_day": "2021-10-05"},
    }

    return {
        "plant_day": dictAgro[crop]["plant_day"].replace("2021", year),
        "harvest_day": dictAgro[crop]["harvest_day"].replace("2021", year),
    }


def computeCrop(general_df: pd.DataFrame, weather_fname: str, uuid_code: str):
    cols = ["crop", "year", "WOFOST_FLD", "weather_uuid"]
    weather = prepareWeather(weather_fname)
    df = pd.DataFrame(columns=cols)

    cropsDict = {
        "barley": "Spring_barley_301",
        "soybean": "Soybean_901",
        "sunflower": "Sunflower_1101",
        "maize": "Grain_maize_201",
        "sugarbeet": "Sugarbeet_603",
    }

    crops = ["barley", "soybean", "sugarbeet"]
    for crop in crops:
        for year in range(2015, 2020):
            cropCal = getCropCalendar(crop, str(year))
            crop_model_yield = run_wofost(
                weather=weather,
                sowing_date=cropCal["plant_day"],
                harvesting_date=cropCal["harvest_day"],
                crop_name=crop,
                crop_variety=cropsDict[crop],
                crop_end_type="harvest",
            )
            # water_limited_df = pd.DataFrame(crop_model_yield["FLD"])
            water_limited_yield = crop_model_yield["FLD"][-1]["TWSO"]
            df.loc[len(df)] = [crop, year, water_limited_yield, uuid_code]
    return pd.concat([general_df, df])


def checkIrrad(df: pd.DataFrame) -> pd.DataFrame:
    df = df.applymap(lambda x: 0 if x < 0 else x)
    df = df.applymap(lambda x: 40000000 - 1 if x > 40000000 else x)
    return df


def checkVAP(df: pd.DataFrame) -> pd.DataFrame:
    df = df.applymap(lambda x: 0.07 if x < 0.06 else x)
    df = df.applymap(lambda x: 199.3 - 1 if x > 199.3 else x)
    return df

def checkWind(df: pd.DataFrame) -> pd.DataFrame:
    df = df.applymap(lambda x: 0.07 if x < 0.00 else x)
    return df

def product_columns(n: int, x1: int, x2: int):
    logging.info(f"Compute weather scenarios: {x1} {x2}")
    print(f"Compute weather scenarios: {x1} {x2}")
    cols = ["crop", "year", "WOFOST_FLD", "weather_uuid"]

    try:
        dirname_out = "/gpfs/gpfs0/gasanov_lab/WOFOST/"
        valid_df = pd.read_csv(os.path.join(dirname_out, f"WOFOST_{x1}_{x2}.csv"))
        if len(valid_df)==96000:
            print('All simulations done!')
            return 'Finished'
    except Exception as e:
        pass
    general_df = pd.DataFrame(columns=cols)
    dirname = "/trinity/home/m.gasanov/agriculture/3s-Article/predicted_weather/"
    logging.info("Read weather files")
    irrad = pd.read_csv(os.path.join(dirname, "interval_data/irrad.csv"))
    irrad = checkIrrad(irrad)
    tmin = pd.read_csv(os.path.join(dirname, "interval_data/tmin.csv"))
    tmax = pd.read_csv(os.path.join(dirname, "interval_data/tmax.csv"))
    vap = pd.read_csv(os.path.join(dirname, "interval_data/vap.csv"))
    vap = checkVAP(vap)
    wind = pd.read_csv(os.path.join(dirname, 'interval_data/wind.csv'))
    wind = checkWind(wind)
    rain = pd.read_csv(os.path.join(dirname, "interval_data/rain.csv"))
    low = pd.read_csv(os.path.join(dirname, "prophet_low.csv"))
    for x3 in range(n + 1):
        for x4 in range(n + 1):
            for x5 in range(n + 1):
                for x6 in range(n + 1):
                    tmp = low[["DAY"]].copy()
                    tmp["IRRAD"] = irrad[f"IRRAD_{x1}"]
                    tmp["TMIN"] = tmin[f"TMIN_{x2}"]
                    tmp["TMAX"] = tmax[f"TMAX_{x3}"]
                    tmp["VAP"] = vap[f"VAP_{x4}"]
                    tmp["WIND"] = wind[f"WIND_{x5}"]
                    tmp["RAIN"] = rain[f"RAIN_{x6}"]
                    tmp["SNOWDEPTH"] = low[["SNOWDEPTH"]]
                    fname = os.path.join(
                        dirname, f"interval_data/{x1}_{x2}_{x3}_{x4}_{x5}_{x6}.csv"
                    )

                    weather_uuid = f"{x1}_{x2}_{x3}_{x4}_{x5}_{x6}"
                    tmp.to_csv(fname, index=False)

                    general_df = computeCrop(
                        general_df=general_df,
                        weather_fname=fname,
                        uuid_code=weather_uuid,
                    )
                    os.remove(fname)
                    path_to_WOFOST_weather = os.path.splitext(fname)[0] + "_WOFOST.csv"
                    os.remove(path_to_WOFOST_weather)
                    # save data
                    if len(general_df) % 1000 == 0:
                        dirname_out = "/gpfs/gpfs0/gasanov_lab/WOFOST/"
                        general_fname = os.path.join(dirname_out, f"WOFOST_{x1}_{x2}.csv")
                        general_df.to_csv(general_fname, index=False)

    return general_df


def main(x1: int, x2: int):
    all_files = product_columns(n=8, x1=x1, x2=x2)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        format="- %(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser()

    parser.add_argument("--x1", default=0, type=int)
    parser.add_argument("--x2", default=0, type=int)
    args = parser.parse_args()
    main(x1=args.x1, x2=args.x2)
