import random
import numpy as np
import time
import sys

batch_size, conf_size = int(sys.argv[1]), sys.argv[2]
t1 = time.time()
# One day has 86400 seconds
day = 86400
xmax, ymax, zmax, mmax = day, day, 7*day, 2*day 
oid, pid, wid, cid, tid, iid = 0, 0, 0, 0, 0, 0
uids = list(range(10000)) 
random.shuffle(uids)
res = []
default_item_id_quantity_mapping = "{'cast iron': 2, 'chainmail cleaner': 1}"

for uid in uids:
	# slightly random ids
	oid, pid, wid, cid, tid, iid = oid + random.randint(1,5), pid + random.randint(1,5), wid + random.randint(1,5), cid + random.randint(1,5), tid + random.randint(1,5), iid + random.randint(1,5) 
	# Start of the event chain
	z0 = random.randint(0,day)
	place_order = {"event_type_name": "place_order", "user_id": str(uid), 'order_id': str(oid), 'item_id_quantity_mapping': default_item_id_quantity_mapping, 'payment_method': 'apple pay', 'payment_amount': random.randint(90,10e5)/100,'payment_tracking_id': str(pid), "event_time": z0}
	z1a = z0 + np.clip((int(xmax*(0.5+np.random.normal(0,1)))),1,xmax-1)
	z1b = z0 + np.clip((int(xmax*(0.5+np.random.normal(0,1)))),1,xmax-1)
	picking = {"event_type_name": "picking", 'order_id': str(oid), 'item_id': "cast iron", 'warehouse_id': str(wid), "event_time": z1a}
	picking = {"event_type_name": "picking", 'order_id': str(oid), 'item_id': "chainmail cleaner", 'package_id': str(pid), 'warehouse_id': str(wid), "event_time": z1b}	
	z2 = max(z1a, z1b) + np.clip((int(ymax*(0.5+np.random.normal(0,1)))),1,ymax-1)
	packing = {"event_type_name": "packing", 'order_id': str(oid), 'package_id': str(pid), 'item_id_quantity_mapping': default_item_id_quantity_mapping, 'warehouse_id': str(wid), "event_time": z2}
	z3 = z2 + np.clip((int(ymax*(0.5+np.random.normal(0,1)))),1,ymax-1)
	assign_carrier = {"event_type_name": "assign_carrier", 'package_id': str(pid), 'warehouse_id': str(wid), 'carrier_id': str(cid), "event_time": z3}
	z4 = z3 + np.clip((int(zmax*(0.5+np.random.normal(0,1)))),1,zmax-1)
	print_shipping_label = {"event_type_name": "print_shipping_label", 'package_id': str(pid), 'warehouse_id': str(wid), 'carrier_id': str(cid), 'tracking_number': str(tid), "event_time": z4}
	ship = {"event_type_name": "ship", 'package_id': str(pid), 'warehouse_id': str(wid), 'carrier_id': str(cid), 'tracking_number': str(tid), "event_time": z4+1}
	z5 = z4 + np.clip((int(mmax*(0.5+np.random.normal(0,1)))),1,mmax-1)
	deliver = {"event_type_name": "deliver", 'package_id': str(pid), 'carrier_id': str(cid), 'tracking_number': str(tid), "event_time": z5}
	for j in range(int(conf_size)):
		confirm_delivery = {"confirm_id": str(j), "event_type_name": "confirm_delivery", 'package_id': str(pid), 'carrier_id': str(cid), 'tracking_number': str(tid), "event_time": z5+1}
		res.append(confirm_delivery)	
	res.extend([place_order, picking, packing, assign_carrier, print_shipping_label, ship, deliver])

res.sort(key=lambda x: x["event_time"])

batchid= 0
loc = f"./sample_events/online_shopping_events-batch_size_{batch_size}-conf_size_{conf_size}.txt"
with open(loc, "a") as f:
	batch = ""
	batch_count = 0
	for i in res:
		batch_count += 1
		s = ""
		curr = 0
		for k,v in i.items():
			s += f"{k}: {v}; "
			if k=="event_time":
				curr = v
		s = s[:-2]
		batch += '{'+f"{s}"+"}\n"
		if batch_count % batch_size == 0:
			f.write(f"{batchid}: {curr}\n{batch}END\n")
			batchid += 1
			batch = ""

#print(*res, sep='\n')
print(f"Time taken: {time.time() - t1}s")

'''
Events:
place_order = {'user_id': 'TEXT', 'order_id': 'TEXT', 'item_id_quantity_mapping': 'TEXT',
                                   'payment_method': 'TEXT', 'payment_amount': 'INTEGER',
                                   'payment_tracking_id': 'TEXT'}
picking = {'order_id': 'TEXT', 'item_id': 'TEXT', 'warehouse_id': 'TEXT', 'package_id': 'TEXT'}
packing = {'order_id': 'TEXT', 'package_id': 'TEXT', 'item_id_quantity_mapping': 'TEXT', 'warehouse_id': 'TEXT'}
assign_carrier = {'package_id': 'TEXT', 'warehouse_id': 'TEXT', 'carrier_id': 'TEXT'}
print_shipping_label = {'package_id': 'TEXT', 'warehouse_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'}
ship = {'package_id': 'TEXT', 'warehouse_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'}
deliver = {'package_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'}
confirm_delivery = {'confirm_id': 'TEXT', 'package_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'}
'''
