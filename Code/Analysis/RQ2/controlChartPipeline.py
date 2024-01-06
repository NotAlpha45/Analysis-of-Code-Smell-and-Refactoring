import math

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def column_to_title(column_name):
    words = column_name.split('_')
    words = [word for word in words if word not in ['total', 'debt']]
    title_words = [word.capitalize() for word in words[:-1]]
    title_words.append('of')
    title_words.append(words[-1].capitalize())
    return ' '.join(title_words)

def plot_control_charts(df, combined_columns, versions):
    num_plots = sum(len(cols) for cols in combined_columns)
    num_cols = len(versions)
    num_rows = math.ceil(num_plots / num_cols)

    fig, axs = plt.subplots(num_rows, num_cols, figsize=(24, 12*num_rows))

    # If there's only one row, axs is a 1D array
    if num_rows == 1:
        axs = np.reshape(axs, (1, -1))

    plot_counter = 0
    # Create line plots
    for i, cols in enumerate(combined_columns):
        for j, col_name in enumerate(cols):
            row = plot_counter // num_cols
            col = plot_counter % num_cols

            # Calculate mean and standard deviation for each column
            mean = df[col_name].mean()
            std = df[col_name].std()

            # Calculate LCL and UCL for each column
            lcl = mean - 3*std
            ucl = mean + 3*std

            # Plot the data
            sns.lineplot(x=versions[j], y=col_name, data=df, ax=axs[row, col], marker ='o')
            axs[row, col].axhline(lcl, color='b', linestyle='--')
            axs[row, col].axhline(ucl, color='r', linestyle='--')
            axs[row, col].axhline(mean, color='g', linestyle='--')
            axs[row, col].set_title(column_to_title(col_name))
            axs[row, col].set_xticklabels(axs[row, col].get_xticklabels(), rotation=90)

            plot_counter += 1

    plt.tight_layout()
    plt.show()

# Usage:
# combined_columns = list(zip(columns_for_controlChart_of_react, columns_for_controlChart_of_vue, columns_for_controlChart_of_svelte))
# plot_control_charts(df_combined, combined_columns, ['version_of_react', 'version_of_vue', 'version_of_svelte'])