import aiohttp, asyncio
from aiohttp_requests import requests
from operator import itemgetter


class Seco:
    def __init__(self,
                 client,
                 token,
                 project,
                 def_bal: int = 0,
                 def_bank: int = 0,
                 default_items={},
                 logs=True):
        self.token = token
        self.project = project
        self.queue = []
        self.cache = []
        self.info = {}
        self.def_bal = def_bal
        self.def_bank = def_bank
        self.default_items = default_items
        self.logs = logs

        client.loop.create_task(self.queue_loop())

    async def queue_loop(self):
        await self.setup()

        #Needed functions
        async def insert_one(data, table):
            try:
                r = await requests.post(f"https://simpleco.xyz/database",
                                        headers={"Auth": self.token},
                                        json={
                                            "project": self.project,
                                            "table": table,
                                            "action": "INSERT",
                                            "values": data
                                        })
                data = await r.json()
                if data.get("ERROR", False) == None:
                    if self.logs:
                        print("Inserted user")
                elif data["ERROR"] == None:
                    if self.logs:
                        print("Inserted user")
                else:

                    print(data["ERROR"])
            except Exception as E:
                print(E)

        async def update_one(data, table, update):
            try:
                r = await requests.post(f"https://simpleco.xyz/database",
                                        headers={"Auth": self.token},
                                        json={
                                            "project": self.project,
                                            "table": table,
                                            "action": "UPDATE",
                                            "values": data,
                                            "update": update
                                        })
                data = await r.json()
                if data.get("ERROR", False) == None:
                    if self.logs:
                        print("UPDATED user")
                elif data["ERROR"] == None:
                    if self.logs:
                        print("UPDATED user")
                else:

                    print(data["ERROR"])
            except Exception as E:
                print(E)

        while True:
            if len(self.queue) != 0:
                for item in self.queue:
                    self.queue.remove(item)
                    for i, value in item.items():
                        if i == "INSERT":
                            await insert_one(value["data"]["in"],
                                             value["data"]["table"])
                        elif i == "UPDATE":
                            await update_one(value["data"]["in"],
                                             value["data"]["table"],
                                             value["data"]["update"])

            await asyncio.sleep(0.05)

    async def setup(self):
        try:
            r = await requests.get(f"https://simpleco.xyz/data/{self.project}",
                                   headers={"Auth": self.token})
            data = await r.json()
            self.cache = data["data"]
            self.info = data["info"]
            if self.logs:
                print("Setup succesful.")
        except Exception as E:
            print(E)
            print("Failed to setup database!")

    async def get_balance(self, userid: int):
        """
        Gets balance by users id
        """
        if len(self.cache["users"]) == 0:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bal)
        search = next(item for item in self.cache["users"]
                      if item["userid"] == str(userid))
        if search == None:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bal)
        return int(search["balance"])

    async def get_bank(self, userid: int):
        """
        Gets bank by users id
        """
        if len(self.cache["users"]) == 0:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bank)
        search = next(item for item in self.cache["users"]
                      if item["userid"] == str(userid))
        if search == None:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bank)
        return int(search["bank"])

    async def add_balance(self, userid: int, amount: int):
        """
        Adds balance to users id
        """
        if len(self.cache["users"]) == 0:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal + amount,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal + amount),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bal + amount)
        search = next(item for item in self.cache["users"]
                      if item["userid"] == str(userid))
        if search == None:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal + amount,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal + amount),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            return int(self.def_bal + amount)

        self.cache["users"].remove(search)
        self.cache["users"].append({
            "balance":
            str(int(search["balance"]) + amount),
            "bank":
            str(int(search["bank"])),
            "userid":
            str(userid)
        })

        self.queue.append({
            "UPDATE": {
                "data": {
                    "in": {
                        "userid": userid
                    },
                    "table": "users",
                    "update": {
                        "balance": int(search["balance"]) + amount
                    }
                }
            }
        })
        return int(search["balance"]) + amount

    async def add_bank(self, userid: int, amount: int):
        """
        Adds balance to users id
        """
        if len(self.cache["users"]) == 0:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank + amount,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank + amount),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bank + amount)
        search = next(item for item in self.cache["users"]
                      if item["userid"] == str(userid))
        if search == None:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank + amount,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank + amount),
                "userid": str(userid)
            })
            return int(self.def_bank + amount)

        self.cache["users"].remove(search)
        self.cache["users"].append({
            "balance": str(int(search["balance"])),
            "bank": str(int(search["bank"]) + amount),
            "userid": str(userid)
        })

        self.queue.append({
            "UPDATE": {
                "data": {
                    "in": {
                        "userid": userid
                    },
                    "table": "users",
                    "update": {
                        "bank": int(search["bank"]) + amount
                    }
                }
            }
        })
        return int(search["bank"]) + amount

    async def remove_bank(self, userid: int, amount: int):
        """
        Adds balance to users id
        """
        if len(self.cache["users"]) == 0:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal - amount,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank - amount),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bank - amount)
        search = next(item for item in self.cache["users"]
                      if item["userid"] == str(userid))
        if search == None:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal,
                            "bank": self.def_bank - amount,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal),
                "bank": str(self.def_bank - amount),
                "userid": str(userid)
            })
            return int(self.def_bank - amount)

        self.cache["users"].remove(search)
        self.cache["users"].append({
            "balance": str(int(search["balance"])),
            "bank": str(int(search["bank"]) - amount),
            "userid": str(userid)
        })

        self.queue.append({
            "UPDATE": {
                "data": {
                    "in": {
                        "userid": userid
                    },
                    "table": "users",
                    "update": {
                        "bank": int(search["bank"]) - amount
                    }
                }
            }
        })
        return int(search["bank"]) - amount

    async def remove_balance(self, userid: int, amount: int):
        """
        Adds balance to users id
        """
        if len(self.cache["users"]) == 0:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal - amount,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal - amount),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            print("K")
            return int(self.def_bal + amount)
        search = next(item for item in self.cache["users"]
                      if item["userid"] == str(userid))
        if search == None:
            self.queue.append({
                "INSERT": {
                    "data": {
                        "in": {
                            "balance": self.def_bal - amount,
                            "bank": self.def_bank,
                            "userid": userid
                        },
                        "table": "users"
                    }
                }
            })
            self.cache["users"].append({
                "balance": str(self.def_bal - amount),
                "bank": str(self.def_bank),
                "userid": str(userid)
            })
            return int(self.def_bal - amount)

        self.cache["users"].remove(search)
        self.cache["users"].append({
            "balance":
            str(int(search["balance"]) - amount),
            "bank":
            str(int(search["bank"])),
            "userid":
            str(userid)
        })

        self.queue.append({
            "UPDATE": {
                "data": {
                    "in": {
                        "userid": userid
                    },
                    "table": "users",
                    "update": {
                        "balance": int(search["balance"]) - amount
                    }
                }
            }
        })
        return int(search["balance"]) - amount
