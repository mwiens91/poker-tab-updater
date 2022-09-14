"""Contains the main function and other functionality."""

import locale
import json
import os
import sys
import gspread
import PySimpleGUI as sg
from oauth2client.service_account import ServiceAccountCredentials
from pokertabupdater.constants import CONFIG_PATH, CREDS_PATH


def get_config_dict() -> dict[str, str]:
    """Parses the config JSON."""
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    return config


def get_sheet(sheet_key: str) -> gspread.worksheet.Worksheet:
    """Gets the main spreadsheet."""
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        CREDS_PATH,
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)
    sheets = client.open_by_key(sheet_key)

    return sheets.get_worksheet(0)


def parse_ledger(ledger: str) -> dict[str, float]:
    """Parses a ledger and returns deltas dict."""

    deltas = {}

    # Note that we're going to be very flexible with the user input here
    lines = [line.strip() for line in filter(len, ledger.splitlines())]

    # Now we'll parse the lines. There are two formats we need to
    # potentially worry about here. On Firefox, the ledger will be
    # copy-pasted as
    #
    # PLAYERNAME @ SOMEID
    # BUYIN BUYOUT STACK NET
    #
    # where this pattern is repeated for each player. On Chrome, it
    # copy-pastes each player's data in one line:
    #
    # PLAYERNAME @ SOMEID BUYIN BUYOUT STACK NET
    #
    # Technically the string "DETAILS" (which is grabbed from a button
    # using that string) is appended to the ID, but we aren't using the
    # IDs from the ledger so this doesn't really matter for our
    # purposes.
    #
    # How we're going to differentiate them is by how many elements
    # there are on the first line when we split by whitespace. If there
    # are more than 3, then it's the Chrome format. Otherwise, it'll be
    # the Firefox format.
    is_firefox_format = len(lines[0].split()) < 4

    # Now, depending on the format, we'll group the data differently
    # when we iterate through it. For Firefox format, we'll group the
    # lines pairwise; for Chrome format, line-by-line is obviously fine.
    iter_lines = zip(*[iter(lines)] * 2) if is_firefox_format else lines

    for iter_line in iter_lines:
        # Parse the line(s)
        if is_firefox_format:
            l1, l2 = iter_line
            player_name_raw = " ".join(l1.split()[:-2])
            player_data = [float(x) for x in l2.split()]
        else:
            l_split = iter_line.split()
            player_name_raw = " ".join(l_split[:-6])
            player_data = [float(x) for x in l_split[-4:]]

        player_name = player_name_raw.lower().title()
        delta = player_data[3]

        deltas[player_name] = delta

    return deltas


def update_sheet(sheet: gspread.worksheet.Worksheet, deltas_dict: dict[str, float]):
    """Updates the spreadsheet with given deltas.

    Note that cell indices are start at 1, so *_sheet_idx corresponds to
    this convention.
    """
    players_col = sheet.col_values(1)

    first_player_idx = next(i for i, j in enumerate(players_col) if j)
    last_player_idx = (
        next(i for i, j in enumerate(players_col[first_player_idx:]) if not j)
        + first_player_idx
        - 1
    )

    first_player_sheet_idx = first_player_idx + 1
    last_player_sheet_idx = last_player_idx + 1

    # Where to put a new row if we need to insert one
    new_row_sheet_idx = last_player_sheet_idx + 1

    # Update or insert rows
    for player, delta in deltas_dict.items():
        # Find row of existing player or make new row with new player
        try:
            row_sheet_idx = players_col.index(player) + 1
            sheet.update_cell(
                row_sheet_idx,
                2,
                sheet.cell(row_sheet_idx, 2, value_render_option="FORMULA").value
                + delta,
            )
        except ValueError:
            sheet.insert_row(
                [
                    player,
                    locale.currency(delta),
                    "",
                    locale.currency(0),
                    locale.currency(0),
                    "=B%d+D%d+E%d"
                    % (new_row_sheet_idx, new_row_sheet_idx, new_row_sheet_idx),
                ],
                new_row_sheet_idx,
                value_input_option="USER_ENTERED",
            )
            sheet.format(
                "B%d:D%d" % (new_row_sheet_idx, new_row_sheet_idx),
                {"numberFormat": {"type": "CURRENCY"}},
            )

            new_row_sheet_idx += 1

    # Sort all the data
    sheet.sort(
        (2, "des"), range="A%d:E%d" % (first_player_sheet_idx, new_row_sheet_idx - 1)
    )

    # Update the row where we sum everything up if we need to
    if last_player_sheet_idx == new_row_sheet_idx - 1:
        return

    last_player_sheet_idx = new_row_sheet_idx - 1

    # Find the row where we have the title "SUM OF OWED/OWING"
    sum_row_sheet_idx = sheet.find("SUM OF OWED/OWING:").row + 1

    # Get the cells we need to update
    sum_cells = sheet.range(sum_row_sheet_idx, 3, sum_row_sheet_idx, 6)

    for i, col_letter in enumerate(["B", "D", "E", "F"]):
        sum_cells[i].value = "=SUM(%s%d:%s%d)" % (
            col_letter,
            first_player_sheet_idx,
            col_letter,
            last_player_sheet_idx,
        )

    sheet.update_cells(
        sum_cells,
        value_input_option="USER_ENTERED",
    )


def main():
    """The main function."""

    # Set locale based on operating system
    if os.name == "nt":
        locale_string = "en-US"
    else:
        locale_string = "en_US.UTF-8"

    locale.setlocale(locale.LC_ALL, locale_string)

    # Window title and layout
    window_title = "Poker tab updater"
    layout = [
        [
            sg.Text(
                "Enter the copy-pasted ledger (make sure the names match the ones on the poker tab!)"
            )
        ],
        [sg.Multiline("", size=(70, 15))],
        [sg.Button("Submit"), sg.Button("Cancel")],
    ]

    # Read config JSON
    config_dict = get_config_dict()

    # Get the sheet
    sheet = get_sheet(config_dict["sheetKey"])

    # Make the window
    window = sg.Window(window_title, layout)

    # Get the input values
    event, input_values = window.read()

    # But get out if the window is closed or cancel is clicked
    if event in [sg.WIN_CLOSED, "Cancel"]:
        window.close()
        sys.exit(0)

    # Get deltas dictionary
    deltas = parse_ledger(input_values[0])

    update_sheet(sheet, deltas)

    window.close()
