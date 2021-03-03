import numpy as np 
import lcls2_inj_dev

save_yag = lcls2_inj_dev.Yag(device="CAMR:LGUN:950")
images = []
for i in range(0,5):
   image = save_yag.acquireImage()
   images.append(image)

stacked = np.stack(images)
np.save('test/test.npy', stacked)
