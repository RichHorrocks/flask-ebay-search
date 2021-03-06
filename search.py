#!/usr/bin/env python

import os
import sys
import pprint
import locale
import time
import datetime
import isodate
import ebaysdk
from ebaysdk.finding import Connection as finding
from ebaysdk.exception import ConnectionError

from flask import Flask
from flask import render_template

FILE_SEARCH = "./search.txt"
FILE_HTML = "./templates/list.html"

HTML_LINK = """<td align="right" style="width:60px">%s%s</td>
               <td align="right" style="width:120px">%s</td>
               <td align="right" style="width:15px">%s</td>
               <td><a href="%s" target="_blank">%s</a></td></tr>"""
HTML_HEADER = '</br>Search string: <b>"%s"</b> ------ Price: %s</br>'
HTML_TIME = """<p><small>Results generated for %d searches in %.3f seconds. \
               Last generated at %s</small></p>"""

# The attributes of the table.
TABLE_OPEN = '<table>'
TABLE_CLOSE = '</table>'

# Instantiate our Flask class.
app = Flask(__name__)


# Decide which URL will trigger everything...
@app.route('/')
def ebay_serve_page():
    return render_template("list.html")

# Check whether we're parsing a comment.


def ebay_is_comment(line):
    return line[:1] == '#'

# Write our constructed HTML strings.


def ebay_write_html(items_to_write):
    with open(FILE_HTML, 'w') as f:
        for item in items_to_write:
            f.write("%s" % item)


# Open the text file containing what to search eBay for.
def ebay_get_wanted_items():
    with open(FILE_SEARCH, 'r') as f:
        items = f.readlines()

    return items


def ebay_find_wanted_items():
    # No need to include our ID here; that gets grabbed from the YAML file.
    api = finding(https=True, siteid='EBAY-GB')

    # Get the search strings from our text file.
    # The amount we're willing to pay is: item.split(' ', 1)[0]
    # The string to search for is: item.split(' ', 1)[1]
    wanted_items = ebay_get_wanted_items()
    wanted_item_count = 0

    # List to hold the lines of html we're going to write to a file.
    items_html_list = []

    # Get the current time, for use in calculating elapsed time.
    time_start = time.time()

    # Query eBay for each wanted item.
    for item in wanted_items:
        if ebay_is_comment(item) or item.isspace():
            continue
        item_price = item.split(' ', 1)[0]
        item_name = item.split(' ', 1)[1]
        wanted_item_count += 1

        response = api.execute('findItemsAdvanced', {
            'keywords': item_name,
            'itemFilter': [
                {'name': 'ListingType',
                 'value': 'Auction'},
                {'name': 'LocatedIn',
                 'value': 'GB'},
                {'name': 'MaxPrice',
                 'value': item_price},
            ],
            'sortOrder': 'EndTimeSoonest',
        })

        # The results are returned as a dictionary.
        item_count = int(response.reply.searchResult._count)
        items_html_list.append(HTML_HEADER % (item_name, item_price))
        items_html_list.append(TABLE_OPEN)

        for i in range(item_count):
            if item_count == 1:
                item = response.reply.searchResult.item[0]
            else:
                item = response.reply.searchResult.item[i]

            total_price = float(item.sellingStatus.currentPrice.value)

            free_postage = True
            if hasattr(item.shippingInfo, 'shippingServiceCost'):
                total_price += float(item.shippingInfo.shippingServiceCost.value)
                free_postage = False

            if total_price < float(item_price):
                date = isodate.parse_duration(item.sellingStatus.timeLeft)

                items_html_list.append(HTML_LINK % (locale.currency(total_price),
                                                    "f" if free_postage else "",
                                                    date,
                                                    item.sellingStatus.bidCount,
                                                    item.viewItemURL,
                                                    item.title.encode('utf-8')))

        items_html_list.append(TABLE_CLOSE)

    dt = datetime.datetime.now().strftime("%A, %d. %B %Y %H:%M")
    items_html_list.append(HTML_TIME % (wanted_item_count,
                                        time.time() - time_start,
                                        dt))
    ebay_write_html(items_html_list)


# Run!
if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, 'en_GB.utf8')
    ebay_find_wanted_items()

    app.debug = True
    app.run("0.0.0.0", port=8887, use_reloader=False)
