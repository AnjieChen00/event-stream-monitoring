import random
import numpy as np
import time
import sys

def getenactmentid(event, okey, pkey):
	eventtype = event["eventtypename"]
	if eventtype in ["placeorder", "picking", "packing"]:
		return okey[event["orderid"]]
	return pkey[event["packageid"]]

def gennext(currevent, idchain, okey, pkey):
	eventtype = currevent["eventtypename"]
#	if (eventtype != "placeorder"): print(eventtype)
	z = currevent["eventtime"]
	nextevent = {}
	if eventtype == "placeorder":
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
	elif eventtype == "confirmdelivery":
		nextevent = {"confirmid": str(j), "eventtypename": "confirmdelivery", 'packageid': currevent["packageid"], 'carrierid': currevent["carrierid"], 'trackingnumber': currevent["trackingnumber"], "eventtime": z+1}
	else:
		print(f"Error: {eventtype} is not a continuing event for this workflow")
	return nextevent

if __name__ == '__main__':
	if len(sys.argv) >= 3:
		batchsize, fid = int(sys.argv[1]), sys.argv[2]
	else:
		batchsize, fid = 100, 1
	random.seed(fid)
	t1 = time.time()
	# One day has 86400 seconds
	day = 86400
	xmax, ymax, zmax, mmax = 5, 5, 30, 10
	idchain = {"orderid": 0, "packageid": 0, "warehouseid": 0, "carrierid": 0, "trackingnumber": 0} 
	res = [[] for y in range(100)]
	defaultitemidquantitymapping = "{'castiron':2}"
	enactmentid = 0
	okey, pkey = {}, {}
	nametoid = {"placeorder": 2, "picking": 3, "packing": 4, "assigncarrier": 5, "printshippinglabel": 6, "ship": 7, "deliver": 8, "confirmdelivery": 9}

	for z in range(1,100):		
		#If not full fill rest with placeorder
		if len(res[z]) < batchsize:
			for i in range(batchsize-len(res[z])):
				placeorder = {"eventtypename": "placeorder", "userid": str(i), 'orderid': str(idchain["orderid"]), 'itemidquantitymapping': defaultitemidquantitymapping, 'paymentmethod': 'applepay', 'paymentamount': random.randint(90,10e5)/100,'paymenttrackingid': str(idchain["packageid"]), "eventtime": z}
				okey[str(idchain["orderid"])] = enactmentid
				idchain["orderid"] += random.randint(1,5)
				res[z].append(placeorder)
				enactmentid += 1
		for currevent in res[z]:
			if currevent["eventtypename"] == "deliver":
				continue
			nextevent = gennext(currevent, idchain, okey, pkey)
			idchain["orderid"] += random.randint(1,5)
			nextz = nextevent["eventtime"]
			if nextz < 100:
				if len(res[nextz]) < batchsize: 
					res[nextz].append(nextevent)

loc = f"./sample_events_no_skipping_issac/online_shopping_events-batchsize_{batchsize}-{fid}.txt"
with open(loc, "a") as f:
	for i in range(1,100):
		out, nout = "", ""
		for currd in res[i]:
			s = f"{i} {getenactmentid(currd, okey, pkey)} {nametoid[currd['eventtypename']]} "	
			for k,v in currd.items():
				if k == "eventtypename":
					s += f"{v}"
				else:
					s += f" {k}={v}"
			s += '\n'
			if (currd["eventtypename"] == "placeorder"):
				out += f"{i-1} {getenactmentid(currd, okey, pkey)} 1 START\n"
			nout += s
			if (currd["eventtypename"] == "deliver") and i != 99:
				out += f"{i+1} {getenactmentid(currd, okey, pkey)} 10 END\n"
		f.write(out)
		f.write(nout)

#sanity check for fixed batchsize
#sizearr = [len(x) for x in res]
#print(sizearr)
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
