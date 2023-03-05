import pandas as pd


def process_data():
    df = pd.read_csv('chipotle_stores.csv', delimiter=',')
    df_dict = df.to_dict(orient='records')
    return df_dict
