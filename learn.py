# import httpx


# response = httpx.get("https://httpbin.org/get")

# print(response.status_code)
# print(response.text)


# print(isinstance(123, (int,float)))


# value = "   Rs. 1,25,000   "
# print(str(value).strip())

#strip() le start and end ko whitespace remove garcha


# from urllib.parse import urlparse

# url = "https://WWW.DARAZ.COM.NP/catalog/?q=iphone"

# parsed_url = urlparse(url)

# print(f"Scheme : {parsed_url.scheme}")
# print(f"Netloc or Domain Name or Hostname : {parsed_url.hostname}")
# print(f"Path : {parsed_url.path}")
# print(f"Query : {parsed_url.query}")

# print(f"Website Name : {parsed_url.hostname.lower().removeprefix("www.")}")



#asyncio in Python 

import time


#synchronous Task
#synchronous ma chai Sequentially Task perform huncha
# at First Euta Task Complete bhaesi arko task complete huncha


# import time

# start_time = time.perf_counter()

# def task_1(t1: int):
#     time.sleep(t1)  # Given time samma wait garcha
#     print(f"Task 1 executed after {t1} seconds")


# def task_2(t2: int):
#     time.sleep(t2)
#     print(f"Task 2 executed after {t2} seconds")


# task_1(2)
# task_2(3)

# end_time = time.perf_counter()

# execution_time = end_time - start_time

# print(f"Total Time: {execution_time:.4f} seconds")


#Output : 5 Second laago


#Let say Hamro Task1 and Task2 chai Asynchronous cha
#which means Both Task chai Concurrently i.e same time ma Run huncha


# import asyncio



# async def task_1(t1 : int):
#   await asyncio.sleep(t1)
#   #yo sleep huda Eslai wait garera arko Task lai perfom garna lai "await" use garne
  
#   print(f"Task1 is Executed in {t1}")


# async def task_2(t2 : int):
#   await asyncio.sleep(t2)
  
#   print(f"Task2 is Executed in {t2}")
  

# async def main():
#   # asyncio.gather(
#   #   await task_1(2),
#   #   await task_2(3)
#   # ) --> Wrong 
  
#   #kina ki hamile await use garesi euta task lai wait garcha and arko Task run huncha
  
#   #both lai concurently run garna lai await use nagarne in gather() bhitra
#   start_time = time.perf_counter()
#   await asyncio.gather(
#     task_1(2),
#     task_2(3)
#   )
#   end_time = time.perf_counter()
#   execution_time = end_time - start_time
#   print(f"Total Time Taken to Execute : {execution_time:.4f}")

# asyncio.run(main())



# import re 

# text = "My name is -ujjwal dahal"

# result = re.findall(r"[a-z0-9]+", text.lower())

# print(result)

