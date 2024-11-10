import random
import numpy as np
import time
import sys
import string
batch_size, fid = int(float(sys.argv[1])), sys.argv[2]
random.seed(fid)
t1 = time.time()
letters = string.ascii_letters
loc = f"./sample_events_icost/icost_events-batch_size_{batch_size}-{fid}.txt"
for i in range(100):
	with open(loc, "a") as f:
		f.write(f"batch_size_{batch_size}-{fid}-{i}: {i}\n")
		for j in range(batch_size):
			account = str(random.randint(10e11,10e12))
			product_code = ''.join(random.choice(letters) for i in range(9))
			service_tag = ''.join(random.choice(letters) for i in range(9))
			start_time = random.randint(1, 10e8) 
			time_diff = random.randint(1, 10e8)
			timestamp_interval = f"{time.strftime('%Y %H:%M:%S', time.gmtime(start_time))}-{time.strftime('%Y %H:%M:%S', time.gmtime(start_time+time_diff))}" 
			icost = random.randint(-10e6, 10e6)
			f.write('{'+f"event_type_name: item_cost; account: {account}; product_code: {product_code}; service_tag: {service_tag}; timestamp_interval: {timestamp_interval}; icost: {icost/10e5}; event_time: {i}"+"}\n")
		f.write("END\n")
print(f"Time taken for batch_size_{batch_size}-{fid}: {time.time() - t1}s")
