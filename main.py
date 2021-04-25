# https://www.mediawiki.org/wiki/API:Links
# https://www.mediawiki.org/wiki/API:Query
# https://www.geeksforgeeks.org/python-communicating-between-threads-set-1/

import requests
import queue
from threading import Thread

_sentinel = "STOP"

class Page:
    def __init__(self, origin, title, depth):
        self.origin = origin
        self.title = title
        self.depth = depth
        self.links = []

def producer(producerToConsumer, consumerToProducer, S, startPage, endPage, language):
    try:
        URL = "https://" + language + ".wikipedia.org/w/api.php"

        endPARAMS = {
            "action": "query",
            "titles": endPage,
            "format": "json",
            "prop": "links",
            "pllimit": 500
        }

        R = S.get(url=URL, params=endPARAMS)
        DATA = R.json()

        try:
            print("No such page", DATA["query"]["pages"]["-1"]["title"], DATA["query"]["pages"]["-1"]["missing"])
            producerToConsumer.put(_sentinel)
            return
        except:
            pass

        PARAMS = {
            "action": "query",
            "titles": startPage,
            "format": "json",
            "prop": "links",
            "pllimit": 500
        }

        R = S.get(url=URL, params=PARAMS)
        DATA = R.json()
        try:
            print("No such page", DATA["query"]["pages"]["-1"]["title"], DATA["query"]["pages"]["-1"]["missing"])
            producerToConsumer.put(_sentinel)
            return
        except:
            pass

        producerToConsumer.put(DATA)

        while True:
            data = consumerToProducer.get()
            if data is _sentinel:
                break
            R = S.get(url=URL, params=data)
            DATA = R.json()
            producerToConsumer.put(DATA)
    except Exception as err:
        print("Error in producer:", err)
        producerToConsumer.put(_sentinel)


def consumer(producerToConsumer, consumerToProducer, startPage, endPage):
    if startPage == endPage:
        print("Start page is the same as end page. Depth is 0.")
        consumerToProducer.put(_sentinel)
        return

    searchedPages = 0
    try:
        pageQueue = []

        initialPage = Page(None, startPage, 0)
        pageQueue.append(initialPage)

        while len(pageQueue) > 0:
            searchedPages += 1
            try:
                data = producerToConsumer.get()
                if data is _sentinel:
                    break
                pages = data["query"]["pages"]
                cont = checkForContinue(data, pageQueue[0].title, endPage)

                if cont != None: # There's still links to go through on the same page
                    for k, v in pages.items():
                        for l in v["links"]:
                            pageQueue[0].links.append(Page(pageQueue[0], l["title"], pageQueue[0].depth + 1))
                            if l["title"] == endPage:
                                print("\nFOOOUND IT! Depth is", pageQueue[0].depth + 1)
                                print("Searched pages", searchedPages)
                                print("Path (backwards):")
                                print(l["title"])
                                print(pageQueue[0].title)
                                original = pageQueue[0].origin
                                while original != None:
                                    print(original.title)
                                    original = original.origin
                                consumerToProducer.put(_sentinel)
                                return
                    consumerToProducer.put(cont)

                elif cont == None: # Time to change pages
                    for k, v in pages.items(): # Go through the last links
                        for l in v["links"]:
                            pageQueue[0].links.append(Page(pageQueue[0], l["title"], pageQueue[0].depth + 1))
                            if l["title"] == endPage:
                                print("\nFOOOUND IT! Depth is", pageQueue[0].depth + 1)
                                print("Searched pages", searchedPages)
                                print("Path (backwards):")
                                print(l["title"])
                                print(pageQueue[0].title)
                                original = pageQueue[0].origin
                                while original != None:
                                    print(original.title)
                                    original = original.origin
                                consumerToProducer.put(_sentinel)
                                return

                    for link in pageQueue[0].links: # Add the links to the pageQueue
                        pageQueue.append(link)
                    pageQueue.pop(0) # And remove the current page from the queue
                    print("\nSearched pages", searchedPages)
                    print("Path so far (backwards):")
                    print(pageQueue[0].title)
                    original = pageQueue[0].origin
                    while original != None:
                        print(original.title)
                        original = original.origin

                    newPageToFetch = {
                    "action": "query",
                    "titles": pageQueue[0].title,
                    "format": "json",
                    "prop": "links",
                    "pllimit": 500
                    }
                    consumerToProducer.put(newPageToFetch)

            except KeyError:
                for link in pageQueue[0].links:
                    pageQueue.append(link)
                pageQueue.pop(0)
                print("\nSearched pages", searchedPages)
                print("Path so far (backwards):")
                print(pageQueue[0].title)
                original = pageQueue[0].origin
                while original != None:
                    print(original.title)
                    original = original.origin
                newPageToFetch = {
                "action": "query",
                "titles": pageQueue[0].title,
                "format": "json",
                "prop": "links",
                "pllimit": 500
                }
                consumerToProducer.put(newPageToFetch)
                continue
    except Exception as err:
        print("Error in consumer:", err)
        consumerToProducer.put(_sentinel)

            

    
# Checks if there's the continue flag in the API response
def checkForContinue(data, currentPage, endPage):
    try:
        PARAMS = {
        "action": "query",
        "titles": currentPage,
        "format": "json",
        "prop": "links",
        "pllimit": 500,
        "plcontinue": data["continue"]["plcontinue"]
        }
        return PARAMS
    except KeyError:
        return None
    except Exception as e:
        print(e)
        return _sentinel


def main():
    language = input("Give wikipedia language (shortened, e.g. en or fi): ").lower()
    startPage = input("Give the start page title: ").capitalize()
    endPage = input("Give the end page title: ").capitalize()

    S = requests.Session()
    producerToConsumer = queue.Queue()
    consumerToProducer = queue.Queue()
    t1 = Thread(target = consumer, args =[producerToConsumer, consumerToProducer, startPage, endPage])
    t2 = Thread(target = producer, args =[producerToConsumer, consumerToProducer, S, startPage, endPage, language])
    t1.start()
    t2.start()

main()