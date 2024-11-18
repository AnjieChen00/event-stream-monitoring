import subprocess
import time
if __name__ == '__main__':
	batch_sizes = [100, 200, 300, 500, 1000, 3000, 5000, 10000]
	t1 = time.time()
	for batch_size in batch_sizes:
		for fid in range(1,4):
			subprocess.call(["python3.11", "./eventgen_online_shopping_no_skipping.py", str(batch_size), str(fid)])
	print(f"Total time taken to finish - {time.time()-t1}s")
