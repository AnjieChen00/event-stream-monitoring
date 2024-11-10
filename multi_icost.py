import subprocess
import time
if __name__ == '__main__':
	batch_sizes = [10e1, 10e2, 10e3, 10e4, 10e5, 10e6]
	t1 = time.time()
	for batch_size in batch_sizes:
		for fid in range(1,4):
			subprocess.call(["python3.11", "./eventgen_icost.py", str(batch_size), str(fid)])
	print(f"Total time taken to finish - {time.time()-t1}s")
