"""Test ImageNet pretrained DenseNet"""
from __future__ import print_function
import sys
# sys.path.insert(0,'Keras-2.0.8')
from multiprocessing.dummy import Pool as ThreadPool
import random
from medpy.io import load
import numpy as np
import argparse
from keras.optimizers import SGD
from keras.callbacks import ModelCheckpoint
import keras.backend as K
from loss import weighted_crossentropy_2ddense
import os
import math
# from keras.utils2.multi_gpu import make_parallel

from keras.utils import multi_gpu_model

from denseunet import DenseUNet
from skimage.transform import resize
K.set_image_dim_ordering('tf')

from tensorflow.python.client import device_lib


#  global parameters
parser = argparse.ArgumentParser(description='Keras 2d denseunet Training')
#  data folder
parser.add_argument('-data', type=str, default='data/', help='test images')
parser.add_argument('-save_path', type=str, default='/content/H-DenseUNet/Experiments/')
#  other paras
parser.add_argument('-b', type=int, default=40)
parser.add_argument('-input_size', type=int, default=224)
parser.add_argument('-model_weight', type=str, default='./model/densenet161_weights_tf.h5')
parser.add_argument('-input_cols', type=int, default=3)

#  data augment
parser.add_argument('-mean', type=int, default=48)
parser.add_argument('-thread_num', type=int, default=14)
args = parser.parse_args()

MEAN = args.mean
thread_num = args.thread_num

def get_available_gpus():
    local_device_protos = device_lib.list_local_devices()
    return [x.name for x in local_device_protos if x.device_type == 'GPU']

liverlist = [32,34,38,41,47,87,89,91,105,106,114,115,119]
def load_seq_crop_data_masktumor_try(Parameter_List):
    img = Parameter_List[0]
    tumor = Parameter_List[1]
    lines = Parameter_List[2]
    numid = Parameter_List[3]
    minindex = Parameter_List[4]
    maxindex = Parameter_List[5]
    #  randomly scale
    scale = np.random.uniform(0.8,1.2)
    deps = int(args.input_size * scale)
    rows = int(args.input_size * scale)
    cols = 3

    sed = np.random.randint(1,numid)
    cen = lines[sed-1]
    cen = np.fromstring(cen, dtype=int, sep=' ')

    a = min(max(minindex[0] + deps/2, cen[0]), maxindex[0]- deps/2-1)
    b = min(max(minindex[1] + rows/2, cen[1]), maxindex[1]- rows/2-1)
    c = min(max(minindex[2] + cols/2, cen[2]), maxindex[2]- cols/2-1)
    cropp_img = img[a - deps / 2:a + deps / 2, b - rows / 2:b + rows / 2,
                c - cols / 2: c + cols / 2 + 1].copy()
    cropp_tumor = tumor[a - deps / 2:a + deps / 2, b - rows / 2:b + rows / 2,
                  c - cols / 2:c + cols / 2 + 1].copy()

    cropp_img -= MEAN
     # randomly flipping
    flip_num = np.random.randint(0, 8)
    if flip_num == 1:
        cropp_img = np.flipud(cropp_img)
        cropp_tumor = np.flipud(cropp_tumor)
    elif flip_num == 2:
        cropp_img = np.fliplr(cropp_img)
        cropp_tumor = np.fliplr(cropp_tumor)
    elif flip_num == 3:
        cropp_img = np.rot90(cropp_img, k=1, axes=(1, 0))
        cropp_tumor = np.rot90(cropp_tumor, k=1, axes=(1, 0))
    elif flip_num == 4:
        cropp_img = np.rot90(cropp_img, k=3, axes=(1, 0))
        cropp_tumor = np.rot90(cropp_tumor, k=3, axes=(1, 0))
    elif flip_num == 5:
        cropp_img = np.fliplr(cropp_img)
        cropp_tumor = np.fliplr(cropp_tumor)
        cropp_img = np.rot90(cropp_img, k=1, axes=(1, 0))
        cropp_tumor = np.rot90(cropp_tumor, k=1, axes=(1, 0))
    elif flip_num == 6:
        cropp_img = np.fliplr(cropp_img)
        cropp_tumor = np.fliplr(cropp_tumor)
        cropp_img = np.rot90(cropp_img, k=3, axes=(1, 0))
        cropp_tumor = np.rot90(cropp_tumor, k=3, axes=(1, 0))
    elif flip_num == 7:
        cropp_img = np.flipud(cropp_img)
        cropp_tumor = np.flipud(cropp_tumor)
        cropp_img = np.fliplr(cropp_img)
        cropp_tumor = np.fliplr(cropp_tumor)

    cropp_tumor = resize(cropp_tumor, (args.input_size,args.input_size,args.input_cols), order=0, mode='edge', cval=0, clip=True, preserve_range=True)
    cropp_img   = resize(cropp_img, (args.input_size,args.input_size,args.input_cols), order=3, mode='constant', cval=0, clip=True, preserve_range=True)
    return cropp_img, cropp_tumor[:,:,1]

# def generate_arrays_from_file(batch_size, trainidx, img_list, tumor_list, tumorlines, liverlines, tumoridx, liveridx, minindex_list, maxindex_list):
def generate_arrays_from_file(batch_size,trainidx):
    while 1:
        X = np.zeros((batch_size, args.input_size, args.input_size, args.input_cols), dtype='float32')
        Y = np.zeros((batch_size, args.input_size, args.input_size, 1), dtype='int16')
        Parameter_List = []
        for idx in xrange(batch_size):
            count = random.choice(trainidx)

            img, img_header = load(args.data+ '/myTrainingData/volume-' + str(count) + '.nii')
            tumor, tumor_header = load(args.data + '/myTrainingData/segmentation-' + str(count) + '.nii')
            maxmin = np.loadtxt(args.data + '/myTrainingDataTxt/LiverBox/box_' + str(count) + '.txt', delimiter=' ')

            minindex = maxmin[0:3]
            maxindex = maxmin[3:6]
            minindex = np.array(minindex, dtype='int')
            maxindex = np.array(maxindex, dtype='int')
            minindex[0] = max(minindex[0] - 3, 0)
            minindex[1] = max(minindex[1] - 3, 0)
            minindex[2] = max(minindex[2] - 3, 0)
            maxindex[0] = min(img.shape[0], maxindex[0] + 3)
            maxindex[1] = min(img.shape[1], maxindex[1] + 3)
            maxindex[2] = min(img.shape[2], maxindex[2] + 3)

            # img = img_list[count]
            # tumor = tumor_list[count]
            # minindex = minindex_list[count]
            # maxindex = maxindex_list[count]

            
            f1 = open(args.data + '/myTrainingDataTxt/TumorPixels/tumor_' + str(idx) + '.txt', 'r')
            tumorline = f1.readlines()
            # tumorlines.append(tumorline)
            # tumoridx.append(len(tumorline))
            f1.close()
            f2 = open(args.data + '/myTrainingDataTxt/LiverPixels/liver_' + str(idx) + '.txt', 'r')
            liverline = f2.readlines()
            # liverlines.append(liverline)
            # liveridx.append(len(liverline))
            f2.close()




            num = np.random.randint(0,6)
            if num < 3 or (count in liverlist):
                lines = liverline
                numid = len(liverline)
            else:
                lines = tumorline
                numid = len(tumorline)
            Parameter_List.append([img, tumor, lines, numid, minindex, maxindex])
        pool = ThreadPool(thread_num)
        result_list = pool.map(load_seq_crop_data_masktumor_try, Parameter_List)
        pool.close()
        pool.join()
        for idx in xrange(len(result_list)):
            X[idx, :, :, :] = result_list[idx][0]
            Y[idx, :, :, 0] = result_list[idx][1]
        # print("getsizeof X, y", sys.getsizeof(X)*1.0/1024/1024, sys.getsizeof(Y)*1.0/1024/1024)
        yield (X,Y)


def load_fast_files(args, trainidx):

    
    img_list = []
    tumor_list = []
    minindex_list = []
    maxindex_list = []
    tumorlines = []
    tumoridx = []
    liveridx = []
    liverlines = []
    number_sample = 0
    for idx in trainidx:
        print(idx)
        img, img_header = load(args.data+ '/myTrainingData/volume-' + str(idx) + '.nii')
        (x, y, z) = img.shape
        number_sample = int(z) + int(number_sample)
        # tumor, tumor_header = load(args.data + '/myTrainingData/segmentation-' + str(idx) + '.nii')
        # img_list.append(img)
        # tumor_list.append(tumor)

        # maxmin = np.loadtxt(args.data + '/myTrainingDataTxt/LiverBox/box_' + str(idx) + '.txt', delimiter=' ')
        # minindex = maxmin[0:3]
        # maxindex = maxmin[3:6]
        # minindex = np.array(minindex, dtype='int')
        # maxindex = np.array(maxindex, dtype='int')
        # minindex[0] = max(minindex[0] - 3, 0)
        # minindex[1] = max(minindex[1] - 3, 0)
        # minindex[2] = max(minindex[2] - 3, 0)
        # maxindex[0] = min(img.shape[0], maxindex[0] + 3)
        # maxindex[1] = min(img.shape[1], maxindex[1] + 3)
        # maxindex[2] = min(img.shape[2], maxindex[2] + 3)
        # minindex_list.append(minindex)
        # maxindex_list.append(maxindex)
        # f1 = open(args.data + '/myTrainingDataTxt/TumorPixels/tumor_' + str(idx) + '.txt', 'r')
        # tumorline = f1.readlines()
        # tumorlines.append(tumorline)
        # tumoridx.append(len(tumorline))
        # f1.close()
        # f2 = open(args.data + '/myTrainingDataTxt/LiverPixels/liver_' + str(idx) + '.txt', 'r')
        # liverline = f2.readlines()
        # liverlines.append(liverline)
        # liveridx.append(len(liverline))
        # f2.close()
        # print("trainidx", sys.getsizeof(trainidx)*1.0/1024/1024)
        # print("img_list", sys.getsizeof(img_list)*1.0/1024/1024)
        # print("tumor_list", sys.getsizeof(tumor_list)*1.0/1024/1024)
        # print("tumorlines", sys.getsizeof(tumorlines)*1.0/1024/1024)
        # print("liverlines", sys.getsizeof(liverlines)*1.0/1024/1024)
        # print("tumoridx", sys.getsizeof(tumoridx)*1.0/1024/1024)
        # print("liveridx", sys.getsizeof(liveridx)*1.0/1024/1024)
        # print("minindex_list", sys.getsizeof(minindex_list)*1.0/1024/1024)
        # print("maxindex_list", sys.getsizeof(maxindex_list)*1.0/1024/1024)
        # print("number_sample", sys.getsizeof(number_sample)*1.0/1024/1024)


    # print('-'*30)
    # print('tumor_list', tumor_list[0])
    # print('-'*30)

    # print('-'*30)
    # print('liverlines', liverlines[0])
    # print('-'*30)

    # print('-'*30)
    # print('tumoridx', tumoridx[0])
    # print('-'*30)


    # print('-'*30)
    # print('liveridx', liveridx[0])
    # print('-'*30)

    # print('-'*30)
    # print('minindex_list', minindex_list[0])
    # print('-'*30)

    # print('-'*30)
    # print('maxindex_list', maxindex_list[0])
    # print('-'*30)

    # return trainidx, img_list, tumor_list, tumorlines, liverlines, tumoridx, liveridx, minindex_list, maxindex_list, number_sample
    return number_sample

def train_and_predict():
    number_train = 15
    trainidx = list(range(number_train))
    validx = list(range(31, 33))
    # trainidx, img_list, tumor_list, tumorlines, liverlines, tumoridx, liveridx, minindex_list, maxindex_list, number_sample = load_fast_files(args)
    number_samples = load_fast_files(args, trainidx)
    number_samples_val = load_fast_files(args, validx)
    print("get_available_gpus ", get_available_gpus())

    print('-'*30)
    print('Creating and compiling model...')
    print('-'*30)

    

    model = DenseUNet(reduction=0.5, args=args,nb_dense_block=4, growth_rate=12,nb_filter=24)
    # model.load_weights(args.model_weight, by_name=True)
    # model = make_parallel(model, args.b / 10, mini_batch=10)
    # model = multi_gpu_model(model, gpus=None)
    sgd = SGD(lr=1e-3, momentum=0.9, nesterov=True)
    model.compile(optimizer=sgd, loss=[weighted_crossentropy_2ddense], metrics=['accuracy'])
    model.summary()
    

    print('-'*30)
    print('Fitting model......')
    print('-'*30)

    if not os.path.exists(args.save_path):
        os.mkdir(args.save_path)

    if not os.path.exists(args.save_path + "/model"):
        os.mkdir(args.save_path + '/model')
        os.mkdir(args.save_path + '/history')
    else:
        if os.path.exists(args.save_path+ "/history/lossbatch.txt"):
            os.remove(args.save_path + '/history/lossbatch.txt')
        if os.path.exists(args.save_path + "/history/lossepoch.txt"):
            os.remove(args.save_path + '/history/lossepoch.txt')

    model_checkpoint = ModelCheckpoint(args.save_path + '/model/weights.{epoch:02d}-{loss:.2f}.hdf5', monitor='loss', verbose = 1,
                                       save_best_only=False,save_weights_only=False,mode = 'min', period = 1)


    steps = math.ceil(number_samples / args.b)
    steps_val = math.ceil(number_samples_val / args.b)
    print("steps", int(steps))
    print("steps_val", int(steps_val))
    # model.fit_generator(generate_arrays_from_file(args.b, trainidx, img_list, tumor_list, tumorlines, liverlines, tumoridx,
    #                                               liveridx, minindex_list, maxindex_list),steps_per_epoch=steps,
    #                                                 epochs= 6000, verbose = 1, callbacks = [model_checkpoint], max_queue_size=10,
    #                                                 workers=3, use_multiprocessing=True)
    history = model.fit_generator(generate_arrays_from_file(args.b, trainidx),steps_per_epoch=int(steps),validation_data=generate_arrays_from_file(args.b, validx),
                                                    validation_steps=steps_val,
                                                    epochs= 1, verbose = 1, callbacks = [model_checkpoint], max_queue_size=10,
                                                    workers=1, use_multiprocessing=False)

    print ('Finised Training .......')

if __name__ == '__main__':
    train_and_predict()
