import random
import numpy as np
import time
t1 = time.time()
days, bikes, users, batch_size = 5, 100, 20, 100
bids = list(range(0, bikes)) 
random.shuffle(bids)
res = []
for day in range(days):
	for cid in range(users):
		s = int(users * np.random.normal(10,1))
		s = np.clip(s,0,users-1)
		z1 = users * day + s
		z2 = z1 + random.randint(1,users-s)
		bid = bids[users*day+cid]
		rent, ret = {"event_type_name":"rentBike", "bid":bid, "cid":cid, "event_report_time":z1}, {"event_type_name":"returnBike", "bid":bid, "cid":cid, "event_report_time":z2}
		res.extend([rent, ret])
for i in range(2*days):
	for j in range(bikes):
		res.append({"event_type_name":"reportLocation", "bid":j, "event_report_time":10*i})
res.sort(key=lambda x: x["event_report_time"])
batchid = 0
with open("events.txt", "a") as f:
	batch = ""
	batch_count = 0
	for i in res:
		batch_count += 1
		s = ""
		curr = 0
		for k,v in i.items():
			s += f"{k}: {v}, "
			if k=="event_report_time":
				curr = v
		s = s[:-2]
		batch += '{'+f"{s}"+"}\n"
		if batch_count % batch_size == 0:
			f.write(f"{batchid}: {curr}\n{batch}END\n")
			batchid += 1
#print(*res, sep='\n')
print(f"Time taken: {time.time() - t1}s")
