# poker tab updater

This is a simple GUI app that takes copy-pasted poker ledgers from
[Poker Now](https://www.pokernow.club/) games and modifies a Google
Sheets spreadsheet containing who-owes-what data. Existing players have
their net totals adjusted, new rows are added for new players, all
players are sorted by their amount owed, and spreadsheet functions are
adjusted. The exact format of the spreadsheet you need to use is not
included here (but you can ask me if you really care).

## Usage

While the instructions below will show Unix commands, this program
supports Windows as well.

First install requirements:

```
pip install -r requirements.txt
```

Next, copy the example config file as follows:

```
cp config.json.example config.json
```

Get the key for your Google Sheets spreadsheet (it's the one in
the URL) and enter it into this config file.

After this, you need to get credentials for the Google Sheets API.
There's a good guide how to do this in the first part of
[this page](https://docs.gspread.org/en/latest/oauth2.html).
Once you have the credentials JSON file, rename it `credentials.json`
and put it at the base of the repository.

Finally, run the program with

```
.run_pokertabupdater.py
```
