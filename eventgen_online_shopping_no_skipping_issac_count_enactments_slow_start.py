import random
import numpy as np
import time
import sys
import json
import collections
def getenactmentid(event, okey, pkey):
	eventtype = event["eventtypename"]
	if eventtype in ["placeorder", "picking", "packing"]:
		return okey[event["orderid"]]
	return pkey[event["packageid"]]

def gennext(currevent, idchain, okey, pkey, enactmentid):
	eventtype = currevent["eventtypename"]
#	if (eventtype != "placeorder"): print(eventtype)
	z = currevent["eventtime"]
	nextevent = {}
	if eventtype == "start":
		nextevent = {"eventtypename": "placeorder", "userid": str(random.randint(1,1000)), 'orderid': str(idchain["orderid"]), 'itemidquantitymapping': defaultitemidquantitymapping, 'paymentmethod': 'applepay', 'paymentamount': random.randint(90,10e5)/batches,'paymenttrackingid': str(idchain["packageid"]), "eventtime": z+1}
		okey[str(idchain["orderid"])] = currevent["enactmentid"]
		idchain["orderid"] += random.randint(1,5)
	elif eventtype == "placeorder":
		nextevent = {"eventtypename": "picking", 'orderid': currevent["orderid"], 'itemid': "castiron", 'warehouseid': idchain["warehouseid"], "packageid": idchain["packageid"], "eventtime": z + np.clip((int(xmax*(0.5+np.random.normal(0,1)))),1,xmax-1)}
		idchain["warehouseid"] += random.randint(1,5)
		idchain["packageid"] += random.randint(1,5)
	elif eventtype == "picking":
		nextevent = {"eventtypename": "packing", 'orderid': currevent["orderid"], 'packageid': currevent["packageid"], 'itemidquantitymapping': defaultitemidquantitymapping, 'warehouseid': currevent["warehouseid"], "eventtime": z + np.clip((int(ymax*(0.5+np.random.normal(0,1)))),1,ymax-1)}
	elif eventtype == "packing":
		pkey[currevent["packageid"]] = okey[currevent["orderid"]]
		nextevent = {"eventtypename": "assigncarrier", 'packageid': currevent["packageid"], 'warehouseid': currevent["warehouseid"], 'carrierid': idchain["carrierid"], "eventtime": z + np.clip((int(ymax*(0.5+np.random.normal(0,1)))),1,ymax-1)}
		idchain["carrierid"] += random.randint(1,5)
	elif eventtype == "assigncarrier":
		nextevent = {"eventtypename": "printshippinglabel", 'packageid': currevent["packageid"], 'warehouseid': currevent["warehouseid"], 'carrierid': currevent["carrierid"], 'trackingnumber': idchain["trackingnumber"], "eventtime": z + np.clip((int(zmax*(0.5+np.random.normal(0,1)))),1,zmax-1)} 
		idchain["trackingnumber"] += random.randint(1,5)
	elif eventtype == "printshippinglabel":
		nextevent = {"eventtypename": "ship", 'packageid': currevent["packageid"], 'warehouseid': currevent["warehouseid"], 'carrierid': currevent["carrierid"], 'trackingnumber': currevent["trackingnumber"], "eventtime": z+1}
	elif eventtype == "ship":
		nextevent = {"eventtypename": "deliver", 'packageid': currevent["packageid"], 'carrierid': currevent["carrierid"], 'trackingnumber': currevent["trackingnumber"], "eventtime": z + np.clip((int(mmax*(0.5+np.random.normal(0,1)))),1,mmax-1)}
	elif eventtype == "deliver":
		nextevent = {"confirmid": 'c'+str(currevent["packageid"]), "eventtypename": "confirmdelivery", 'packageid': currevent["packageid"], 'carrierid': currevent["carrierid"], 'trackingnumber': currevent["trackingnumber"], "eventtime": z+1}
	elif eventtype == "confirmdelivery":
		nextevent = {"eventtypename": "end", "enactmentid": getenactmentid(currevent, okey, pkey), "eventtime": z+1}
	else:
		print(f"Error: {eventtype} is not a continuing event for this workflow")
	return nextevent

if __name__ == '__main__':
	if len(sys.argv) >= 3:
		batchsize, fid = int(sys.argv[1]), sys.argv[2]
	else:
		batchsize, fid = 100, 1
	random.seed(fid)
	batches = 1000
	t1 = time.time()
	# One day has 86400 seconds
	slow_start_batches, slow_start_ratio = 8, 0.125
	day = 86400
	xmax, ymax, zmax, mmax = 5, 5, 30, 10
	idchain = {"orderid": 0, "packageid": 0, "warehouseid": 0, "carrierid": 0, "trackingnumber": 0} 
	res = [[] for y in range(batches)]
	defaultitemidquantitymapping = "{'castiron':2}"
	enactmentid = 0
	okey, pkey = {}, {}
	nametoid = {"placeorder": 2, "picking": 3, "packing": 4, "assigncarrier": 5, "printshippinglabel": 6, "ship": 7, "deliver": 8, "confirmdelivery": 9}

	for z in range(batches):		
		#If not full fill rest with placeorder
		curr_batchsize = batchsize
		if z < slow_start_batches:
			curr_batchsize *= slow_start_ratio
		if len(res[z]) < batchsize:
			factor = batchsize-len(res[z])
			if z < slow_start_batches:
				factor = min(curr_batchsize, factor)
			factor = int(factor)
			for i in range(factor):
				start = {"eventtypename": "start", "enactmentid": enactmentid, "eventtime": z}
				res[z].append(start)
				enactmentid += 1
		for currevent in res[z]:
			if currevent["eventtypename"] == "end":
				continue
			nextevent = gennext(currevent, idchain, okey, pkey, enactmentid)
			idchain["orderid"] += random.randint(1,5)
			nextz = nextevent["eventtime"]
			if nextz < batches:
				if len(res[nextz]) < batchsize: 
					res[nextz].append(nextevent)

loc = f"./sample_events_no_skipping_issac/online_shopping_events-batchsize_{batchsize}-batches_{batches}-{fid}.txt"
with open(loc, "a") as f:
	for i in range(batches):
		s = ""
		for currd in res[i]:
			isenact = 0
			if currd["eventtypename"] == "start":
				s = f"{i} {currd['enactmentid']} 1 START"
				isenact = 1
			elif currd["eventtypename"] == "end":
				s = f"{i} {currd['enactmentid']} 10 END"
				isenact = 1
			else:
				s = f"{i} {getenactmentid(currd, okey, pkey)} {nametoid[currd['eventtypename']]} "
			if isenact == 0:	
				for k,v in currd.items():
					if k == "eventtypename":
						s += f"{v}"
					else:
						s += f" {k}={v}"
			s += '\n'	
			f.write(s)

#sanity check for fixed batchsize
#sizearr = [len(x) for x in res]
#print(sizearr[0])
#see event ratio within each batch
sanitized_res = [[y["eventtypename"] for y in x] for x in res]
freqs = []
for sr in sanitized_res:
	freqs.append(collections.Counter(sr))
ratio_loc = f"./ratios/online_shopping_events-batch_size_{batchsize}-batches_{batches}-{fid}_ratios.txt"
for freq in freqs:
	with open(ratio_loc, "a") as f:
		f.write(json.dumps(freq))
		f.write('\n')
print(f"Time taken for batchsize{batchsize}-{fid}: {time.time() - t1}s")
'''
Events:
placeorder = {'userid': 'TEXT', 'orderid': 'TEXT', 'itemidquantitymapping': 'TEXT',
                                   'paymentmethod': 'TEXT', 'paymentamount': 'INTEGER',
                                   'paymenttrackingid': 'TEXT'}
picking = {'orderid': 'TEXT', 'itemid': 'TEXT', 'warehouseid': 'TEXT', 'packageid': 'TEXT'}
packing = {'orderid': 'TEXT', 'packageid': 'TEXT', 'itemidquantitymapping': 'TEXT', 'warehouseid': 'TEXT'}
assigncarrier = {'packageid': 'TEXT', 'warehouseid': 'TEXT', 'carrierid': 'TEXT'}
printshippinglabel = {'packageid': 'TEXT', 'warehouseid': 'TEXT', 'carrierid': 'TEXT', 'trackingnumber': 'TEXT'}
ship = {'packageid': 'TEXT', 'warehouseid': 'TEXT', 'carrierid': 'TEXT', 'trackingnumber': 'TEXT'}
deliver = {'packageid': 'TEXT', 'carrierid': 'TEXT', 'trackingnumber': 'TEXT'}
confirmdelivery = {'confirmid': 'TEXT', 'packageid': 'TEXT', 'carrierid': 'TEXT', 'trackingnumber': 'TEXT'}
'''
