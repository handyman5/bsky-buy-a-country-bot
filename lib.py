#!usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "atproto",
#     "requests",
#     "sparqlwrapper",
# ]
# ///

import os
import random
import requests
from atproto import Client
from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)


def load_billionaires():
    sparql.setQuery(
        """
# Distinct living non-fictional billionaires
SELECT ?locationLabel ?item ?itemLabel ?itemDescription (MAX(?billion) as ?billions)
WHERE {
  # Billionaires with net worth > 1 billion
  ?item wdt:P2218 ?worth.
  ?item wdt:P19 ?location.
  FILTER(?worth > 1000000000).
  FILTER(?worth < 1000000000000).
  BIND(?worth / 1000000000 AS ?billion).

  # Ensure they are alive
  FILTER NOT EXISTS { ?item wdt:P570 ?dateOfDeath. }

  # Retrieve labels in English
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?locationLabel ?item ?itemLabel ?itemDescription
ORDER BY DESC(?billions)
    """
    )
    results = sparql.query().convert()
    return results["results"]["bindings"]


def load_gdps():
    sparql.setQuery(
        """
# Optimized list of distinct countries with GDP
SELECT DISTINCT ?country ?countryLabel ?flagCode (SAMPLE(?billion) AS ?billion)
WHERE {
  # Retrieve countries
  ?country wdt:P31 wd:Q6256.  # Country (instance of sovereign state)

  # Retrieve GDP (nominal) value
  OPTIONAL { ?country wdt:P2131 ?gdp. }  # GDP nominal (P2131)

  BIND(?gdp / 1000000000 AS ?billion).

  OPTIONAL { ?country wdt:P487 ?flagCode. }

  # Retrieve labels in English
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?country ?countryLabel ?flagCode
ORDER BY DESC(?billion)
"""
    )
    results = sparql.query().convert()
    return results["results"]["bindings"]


def get_client():
    client = Client()
    username = os.environ.get("BSKY_USERNAME")
    password = os.environ.get("BSKY_PASSWORD")
    client.login(username, password)
    return client


def get_comparison():
    bills = load_billionaires()
    gdps = load_gdps()

    person = None
    country = None
    while True:
        try:
            person = random.choice(bills)
            country = random.choice(gdps)
            if "billion" not in country:
                continue
            if float(country["billion"]["value"]) > float(person["billions"]["value"]):
                continue

            post_content = (
                f"{person['itemLabel']['value']} ({person['itemDescription']['value']}), net worth ${float(person['billions']['value']):,.2f} billion"
                + "\n\n"
                + "COULD BUY\n\n"
                + f"{country['countryLabel']['value']} {country['flagCode']['value']}, nominal GDP ${float(country['billion']['value']):,.2f} billion"
            )
            return post_content
        except Exception:
            pass


def send_post(text):
    client = get_client()
    client.send_post(text=text)


if __name__ == "__main__":
    result = get_comparison()
    print(result)
    send_post(result)
