#
# images driver for migration (without FS transfer)
#

import os, tempfile, rpyc, tarfile

img_path = "/var/local/p.haul-fs/"
img_tarfile = "images.tar"
xfer_size = 64 * 1024

def copy_file(s, d):
	while True:
		chunk = s.read(xfer_size)
		if not chunk:
			break
		d.write(chunk)

class phaul_images:
	def __init__(self):
		self.current_iter = 0
		self.current_dir = None
		self.prev_dir = None
		self.img_path = tempfile.mkdtemp("", "", img_path)

	def close(self):
		# Remove images directory here (need CLI option --keep-images)
		pass

	def new_image_dir(self):
		self.prev_dir = self.current_dir
		self.current_iter += 1
		img_dir = "%s/%d" % (self.img_path, self.current_iter)
		print "\tMaking directory %s" % img_dir
		self.current_dir = img_dir
		os.mkdir(img_dir)

	def image_dir_fd(self):
		return os.open(self.current_dir, os.O_DIRECTORY)

	def image_dir(self):
		return self.current_dir

	def prev_image_dir(self):
		return self.prev_dir

	# Images transfer
	# Are there better ways for doing this?

	def sync_imgs_to_target(self, th):
		# Pre-dump doesn't generate any images (yet?)
		# so copy only those from the top dir
		print "Sending images to target"

		print "\tPack"
		tf_name = os.path.join(self.current_dir, img_tarfile)
		tf = tarfile.open(tf_name, "w")
		for img in os.listdir(self.current_dir):
			if img.endswith(".img"):
				print "\t\t-> %s" % img
				tf.add(os.path.join(self.current_dir, img), img)
		tf.close()

		print "\tCopy"
		lfh = open(tf_name, "rb")
		os.unlink(tf_name)
		rfh = th.open_image_tar()
		copy_file(lfh, rfh)

		print "\tUnpack"
		rfh.unpack_and_close()

# This one is created by target
class exposed_images_tar():
	def __init__(self, dir):
		self.dir = dir
		self.fname = os.path.join(dir, img_tarfile)
		self.fh = open(self.fname, "wb")

	def exposed_write(self, chunk):
		return self.fh.write(chunk)

	def exposed_unpack_and_close(self):
		self.fh.close()
		tf = tarfile.open(self.fname, "r")
		os.unlink(self.fname)
		tf.extractall(self.dir)
		tf.close()
