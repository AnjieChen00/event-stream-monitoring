import random
import numpy as np
import time
import sys

def gen_next(curr_event, id_chain):
	event_type = curr_event["event_type_name"]
#	if (event_type != "place_order"): print(event_type)
	z = curr_event["event_time"]
	next_event = {}
	if event_type == "place_order":
		next_event = {"event_type_name": "picking", 'order_id': curr_event["order_id"], 'item_id': "cast iron", 'warehouse_id': id_chain["warehouse_id"], "package_id": id_chain["package_id"], "event_time": z + np.clip((int(xmax*(0.5+np.random.normal(0,1)))),1,xmax-1)}
		id_chain["warehouse_id"] += random.randint(1,5)
		id_chain["package_id"] += random.randint(1,5)
	elif event_type == "picking":
		next_event = {"event_type_name": "packing", 'order_id': curr_event["order_id"], 'package_id': curr_event["package_id"], 'item_id_quantity_mapping': default_item_id_quantity_mapping, 'warehouse_id': curr_event["warehouse_id"], "event_time": z + np.clip((int(ymax*(0.5+np.random.normal(0,1)))),1,ymax-1)}
	elif event_type == "packing":
		next_event = {"event_type_name": "assign_carrier", 'package_id': curr_event["package_id"], 'warehouse_id': curr_event["warehouse_id"], 'carrier_id': id_chain["carrier_id"], "event_time": z + np.clip((int(ymax*(0.5+np.random.normal(0,1)))),1,ymax-1)}
		id_chain["carrier_id"] += random.randint(1,5)
	elif event_type == "assign_carrier":
		next_event = {"event_type_name": "print_shipping_label", 'package_id': curr_event["package_id"], 'warehouse_id': curr_event["warehouse_id"], 'carrier_id': curr_event["carrier_id"], 'tracking_number': id_chain["tracking_number"], "event_time": z + np.clip((int(zmax*(0.5+np.random.normal(0,1)))),1,zmax-1)} 
		id_chain["tracking_number"] += random.randint(1,5)
	elif event_type == "print_shipping_label":
		next_event = {"event_type_name": "ship", 'package_id': curr_event["package_id"], 'warehouse_id': curr_event["warehouse_id"], 'carrier_id': curr_event["carrier_id"], 'tracking_number': curr_event["tracking_number"], "event_time": z+1}
	elif event_type == "ship":
		next_event = {"event_type_name": "deliver", 'package_id': curr_event["package_id"], 'carrier_id': curr_event["carrier_id"], 'tracking_number': curr_event["tracking_number"], "event_time": z + np.clip((int(mmax*(0.5+np.random.normal(0,1)))),1,mmax-1)}
	elif event_type == "confirm_delivery":
		next_event = {"confirm_id": str(j), "event_type_name": "confirm_delivery", 'package_id': curr_event["package_id"], 'carrier_id': curr_event["carrier_id"], 'tracking_number': curr_event["tracking_number"], "event_time": z+1}
	else:
		print(f"Error: {event_type} is not a continuing event for this workflow")
	return next_event

if __name__ == '__main__':
	batch_size, fid = int(sys.argv[1]), sys.argv[2]
	random.seed(fid)
	t1 = time.time()
	# One day has 86400 seconds
	day = 86400
	xmax, ymax, zmax, mmax = 10, 10, 70, 20
	id_chain = {"order_id": 0, "package_id": 0, "warehouse_id": 0, "carrier_id": 0, "tracking_number": 0} 
	res = [[] for y in range(100)]
	default_item_id_quantity_mapping = "{'cast iron': 2}"
	#Init for timestamp 0
	for i in range(batch_size):
		place_order = {"event_type_name": "place_order", "user_id": str(i), 'order_id': str(id_chain["order_id"]), 'item_id_quantity_mapping': default_item_id_quantity_mapping, 'payment_method': 'apple pay', 'payment_amount': random.randint(90,10e5)/100,'payment_tracking_id': str(id_chain["package_id"]), "event_time": 0}
		res[0].append(place_order)
		next_event = gen_next(place_order, id_chain)
		id_chain["order_id"] += random.randint(1,5)		

	for z in range(100):
		for curr_event in res[z]:
			if curr_event["event_type_name"] == "deliver":
				continue
			next_event = gen_next(curr_event, id_chain)
			id_chain["order_id"] += random.randint(1,5)
			next_z = next_event["event_time"]
			if next_z < 100:
				if len(res[next_z]) < batch_size: 
					res[next_z].append(next_event)
		#If not full fill rest with place_order
		if len(res[z]) < batch_size:
			for i in range(batch_size-len(res[z])):
				place_order = {"event_type_name": "place_order", "user_id": str(i), 'order_id': str(id_chain["order_id"]), 'item_id_quantity_mapping': default_item_id_quantity_mapping, 'payment_method': 'apple pay', 'payment_amount': random.randint(90,10e5)/100,'payment_tracking_id': str(id_chain["package_id"]), "event_time": z}
				id_chain["order_id"] += random.randint(1,5)	
				res[z].append(place_order)


loc = f"./sample_events_no_skipping/online_shopping_events-batch_size_{batch_size}-{fid}.txt"
with open(loc, "a") as f:
	batch = ""
	for i in range(100):
		for currd in res[i]:
			s = "{"	
			for k,v in currd.items():
				s += f"{k}: {v}; "
			s = s[:-2]
			s += "}"
			batch += f"{s}"+"\n"
		f.write(f"batch_size_{batch_size}-{fid}-{i}: {i}\n{batch}END\n")
		batch = ""

#sanity check for fixed batch_size
#size_arr = [len(x) for x in res]
#print(size_arr)
print(f"Time taken for batch_size_{batch_size}-{fid}: {time.time() - t1}s")
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
