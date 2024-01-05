import numpy as np
import pandas as pd


def process_dataframes(JSlibraryName, df_adapt, df_consis, df_intention):

    def sortDataframeByReleaseDate(df_adapt, df_consis, df_intention):
        df_adapt = df_adapt.sort_values(by=['date'])
        df_consis = df_consis.sort_values(by=['date'])
        df_intention = df_intention.sort_values(by=['date'])
        return df_adapt, df_consis, df_intention
    
    df_adapt, df_consis, df_intention = sortDataframeByReleaseDate(df_adapt, df_consis, df_intention)



    columns_to_drop = ['security_issues_low', 'reliability_issues_low', 'maintainability_issues_low',
                       'security_issues_medium', 'reliability_issues_medium', 'maintainability_issues_medium',
                       'security_issues_high', 'reliability_issues_high', 'maintainability_issues_high']
    
    columns_to_rename = ['total_debt_low', 'total_debt_medium', 'total_debt_high']
    
    df_adapt = df_adapt.drop(columns_to_drop, axis=1)
    df_consis = df_consis.drop(columns_to_drop, axis=1)
    df_intention = df_intention.drop(columns_to_drop, axis=1)



    def total_sum_of_debt(df, column_name):
        column_name = column_name + '_total_debt_of_' + JSlibraryName
        df[column_name] = df[['total_debt_low', 'total_debt_medium', 'total_debt_high']].sum(axis=1)
        return df

    df_adapt = total_sum_of_debt(df_adapt, 'adaptability')
    df_consis = total_sum_of_debt(df_consis, 'consistency')
    df_intention = total_sum_of_debt(df_intention, 'intentionality')



    def debt_diff(df, column_name):
        new_column_name = column_name + '_total_debt_difference_with_previous_version_of_' + JSlibraryName
        df[new_column_name] = df[column_name + '_total_debt_of_' + JSlibraryName].diff()
        df[new_column_name].iloc[0] = df[column_name + '_total_debt_of_' + JSlibraryName].iloc[0]
        return df

    df_adapt = debt_diff(df_adapt, 'adaptability')
    df_consis = debt_diff(df_consis, 'consistency')
    df_intention = debt_diff(df_intention, 'intentionality')



    def rename_columns(df, column_names, prefix):
        for column_name in column_names:
            df = df.rename(columns={column_name: prefix + '_' + column_name + '_of_' + JSlibraryName})
        return df

    df_adapt = rename_columns(df_adapt, columns_to_rename, 'adaptability')
    df_consis = rename_columns(df_consis, columns_to_rename, 'consistency')
    df_intention = rename_columns(df_intention, columns_to_rename, 'intentionality')


    def process_versions(df):
        df['version'] = df['version'].str.replace('v', '')
        df['version'] = df['version'].apply(lambda x: 'v' + x)
        return df

    df_adapt = process_versions(df_adapt)
    df_consis = process_versions(df_consis)
    df_intention = process_versions(df_intention)


    df_combined = pd.concat([df_adapt, df_consis, df_intention], axis=1)
    df_combined = df_combined.T.drop_duplicates().T

    def rename_columns_of_combined_df(df):
        df = df.rename(columns={'version': 'version_of_' + JSlibraryName, 'date': 'date_of_' + JSlibraryName, 'timestamp': 'timestamp_of_' + JSlibraryName})
        return df

    df_combined = rename_columns_of_combined_df(df_combined)

    return df_combined