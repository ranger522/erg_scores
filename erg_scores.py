import pandas as pd
import streamlit as st
from os.path import splitext, basename, dirname, exists
import openpyxl
import matplotlib.pyplot as plt
from math import floor, ceil



def secBreakdown(time):
    minute = floor(time / 60)
    second = floor(time - minute*60)
    microsec = floor((time - floor(time)) * 1e6)
    return minute, second, microsec


def breakdownTimePrintout(minute, second, microsec):
##    return f"{minute}:{second + round(microsec/1e6, 1)}"
    second = f"0{second}" if second < 10 else second
    return f"{minute}:{second}.{int(microsec/1e5)}"


def datetime2sec(time):
    return time.minute*60 + time.second + time.microsecond/1e6


def sec2timePrintout(time):
    minute, second, microsec = secBreakdown(time)
    return breakdownTimePrintout(minute, second, microsec)


def weightAdjustSplit(split, weight):
    return split if weight is None else round(split * (weight/270)**.222, 1)


def determine_split_bounds(rowers, scores):
    minSplit = scores[rowers[0]]['splits'][0]
    maxSplit = scores[rowers[0]]['splits'][0]

    for rower in rowers:
        for split in scores[rower]['splits']:
            minSplit = min(minSplit, split)
            maxSplit = max(maxSplit, split)

    interval = 5  # bounds for the splits will be multiples of 5 seconds
    # Get bounds
    minBound = (int(minSplit) // interval) * interval
    maxBound = ceil((maxSplit + (maxSplit-minBound) / 5) / interval) * interval

    return [minBound, maxBound]


def determine_range_scale(limits, majorInterval=15, minorInterval=5):
    majorScaleVal = (limits[0] // majorInterval) * majorInterval
    majorScaleVal = majorScaleVal if majorScaleVal >= limits[0] \
        else majorScaleVal + majorInterval

    majorScale = []
    while majorScaleVal <= limits[1]:
        majorScale.append(majorScaleVal)
        majorScaleVal += majorInterval

    minorScaleVal = (limits[0] // minorInterval) * minorInterval
    minorScaleVal = minorScaleVal if minorScaleVal >= limits[0] \
        else minorScaleVal + minorInterval

    minorScale = []
    while minorScaleVal <= limits[1]:
        minorScale.append(minorScaleVal)
        minorScaleVal += minorInterval

    return majorScale, minorScale


def check_headers(headers, sheet):
    for count, el in enumerate(headers):
        cell = sheet.cell(row=1, column=count+1).value
        if cell != el:
            print("The Excel file seems to be formatted incorrectly. Check the column names.")
            input(f"The column names should be, in order:\n\t{', '.join(headers[:-1])}")
            quit()


def scores_to_dict(sheet, weightAdj=False):
    scores = {}

    for i in range(sheet.max_row-1):
        name = sheet.cell(row=i+2, column=1).value
        scores[name] = {}
        weight = sheet.cell(row=i+2, column=2).value if weightAdj else None
        scores[name]['weight'] = weight
        scores[name]['time'] = weightAdjustSplit(datetime2sec(sheet.cell(row=i+2, column=3).value), weight)
        scores[name]['split'] = weightAdjustSplit(datetime2sec(sheet.cell(row=i+2, column=4).value), weight)
        scores[name]['splits'] = []
        for j in range(5, sheet.max_column+1):
            cellVal = sheet.cell(row=i+2, column=j).value
            if cellVal is None:  # if there are no splits (left), dump out
                break
            scores[name]['splits'].append(weightAdjustSplit(datetime2sec(cellVal), weight))

    return scores


def plot_splits(rowers, scores, dist=1000, weightAdjusted=False, showSplits=True, plotsDir=""):
    fig, ax = plt.subplots()
    if len(rowers) == 0:  # Exit if this gets called without any rowers, just in case
        return
    if type(rowers) == str:  # If only a single rower is entered as just their name
        rowers = [rowers]
    colors = ['b', 'r', 'g', 'c', 'm', 'y']  # Colors for plotting
    for count, rower in enumerate(rowers):  # Get data for each rower
        splits = scores[rower]['splits']
        weight = scores[rower]['weight']
        color = colors[count]  # Colors assigned in order rowers were selected
        nSplits = len(splits)
        if showSplits and nSplits > 0:  # Only relevant if there are splits to show
            splitSize = dist / nSplits
            for i in range(nSplits):
                split = splits[i]
                plt.plot(splitSize * (i + 1), split, f'{color}o')
        split = scores[rower]['split']
        lbl = f"{rower}\n{sec2timePrintout(split)}"
        if weightAdjusted:
            lbl = lbl + "\nNo Weight" if weight is None else lbl
        plt.axhline(y=split, color=color, linestyle='--', label=lbl)

    ylim = determine_split_bounds(rowers, scores)
    yMajorRange, yMinorRange = determine_range_scale(ylim)

    ax.set_xlim((0, dist))
    ax.set_ylim((ylim[0], ylim[1]))

    # Label axes and rest of plot
    plt.xlabel('Distance (m)')
    plt.ylabel('Time (sec)')

    ttlStart = "Weight Adjusted " if weightAdjusted else ""
    plt.title(f"{ttlStart}Splits for {', '.join(rowers)}")
    plt.legend(ncol=len(rowers), loc='upper center')

    # An empty directory name means to not save the plot
    if plotsDir != "":
        pre = "Weight Adjusted: " if weightAdjusted else ""
        rowerNames = f"{ttlStart}{', '.join(rowers)}"
        plt.savefig(f"{plotDir}/PNG/{rowerNames}.png")
        plt.savefig(f"{plotDir}/EPS/{rowerNames}.eps")

    ax.grid(True, which='major', color='black', linestyle='-', alpha=.25)
    ax.grid(True, which='minor', color='gray', linestyle='--', alpha=.25)
    ax.minorticks_on()

    st.pyplot(plt)


if __name__ == '__main__':

    file = "Test.xlsx"
    scores_pd = pd.read_excel(file, sheet_name=0)  #, index_col='Name')
    distance = int(pd.read_excel(file, sheet_name=1).values)

    st.set_page_config(page_title="Erg Scores",
                       layout="wide")
    # st.write("""
    # Erg scores here.
    # """)

    # '''
    # Sidebar
    # '''
    code = st.sidebar.text_input(
        "Enter code:"
    )
    if code == "BRRC Henley":
        st.sidebar.header("Please select rowers (no more than 6): ")
        
        rowers = st.sidebar.multiselect(
            "Select the rowers:",
            options=scores_pd["Name"]
        )
        weight = st.sidebar.selectbox(
            "Weight Adjust?",
            options=["No", "Yes"]
        )
        scores_selection = scores_pd.query(
            "Name == @rowers"
        )

        wb = openpyxl.load_workbook("2022-07-17 Henley Erg Test.xlsx")
        sheet = wb[wb.sheetnames[0]]
        scores_weight_yes = scores_to_dict(sheet, True)
        scores_weight_no = scores_to_dict(sheet, False)

        weight_adjust = False if weight == "No" else True
        scores = scores_weight_yes if weight_adjust else scores_weight_no
        plot_splits(rowers, scores, dist=distance, weightAdjusted=weight_adjust)
