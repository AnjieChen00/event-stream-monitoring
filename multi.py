import subprocess
import time
if __name__ == '__main__':
	batch_sizes = [x for x in range(100,1000,100)]
	conf_sizes = [x for x in range(20)]
	t1 = time.time()
	for batch_size in batch_sizes:
		for conf_size in conf_sizes:
			subprocess.call(["python3.11", "./eventgen_online_shopping.py", str(batch_size), str(conf_size)])
	print(f"Total time taken to finish - {time.time()-t1}s")
