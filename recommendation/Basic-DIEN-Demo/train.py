import numpy as np
from data_iterator import DataIterator
import pandas as pd
import tensorflow as tf
import random
from model import Model_DIN_V2_Gru_Vec_attGru_Neg



EMBEDDING_DIM = 18
HIDDEN_SIZE = 18 * 2
ATTENTION_SIZE = 18 * 2
best_auc = 0.0

def prepare_data(input,target,maxlen = None,return_neg=False):
    lengths_x = [len(s[4]) for s in input]
    seqs_mid = [inp[3] for inp in input]
    seqs_cat = [inp[4] for inp in input]
    noclk_seqs_mid = [inp[5] for inp in input]
    noclk_seqs_cat = [inp[6] for inp in input]

    # 如果历史记录的长度超过设定的maxlen，则进行裁剪
    if maxlen is not None:
        new_seqs_mid = []
        new_seqs_cat = []
        new_noclk_seqs_mid = []
        new_noclk_seqs_cat = []
        new_lengths_x = []

        for l_x, inp in zip(lengths_x, input):
            if l_x > maxlen:
                new_seqs_mid.append(inp[3][l_x - maxlen:])
                new_seqs_cat.append(inp[4][l_x - maxlen:])
                new_noclk_seqs_mid.append(inp[5][l_x - maxlen:])
                new_noclk_seqs_cat.append(inp[6][l_x - maxlen:])
                new_lengths_x.append(maxlen)
            else:
                new_seqs_mid.append(inp[3])
                new_seqs_cat.append(inp[4])
                new_noclk_seqs_mid.append(inp[5])
                new_noclk_seqs_cat.append(inp[6])
                new_lengths_x.append(l_x)
        lengths_x = new_lengths_x
        seqs_mid = new_seqs_mid
        seqs_cat = new_seqs_cat
        noclk_seqs_mid = new_noclk_seqs_mid
        noclk_seqs_cat = new_noclk_seqs_cat

        if len(lengths_x) < 1:
            return None, None, None, None

    # 进一步压缩空间，根据
    n_samples = len(seqs_mid)
    max_len_x = np.max(lengths_x)
    neg_samples = len(noclk_seqs_mid[0][0])

    mid_his = np.zeros((n_samples,max_len_x)).astype("int64")
    cat_his = np.zeros((n_samples,max_len_x)).astype("int64")
    noclk_mid_his = np.zeros((n_samples,max_len_x,neg_samples)).astype("int64")
    noclk_cat_his =  np.zeros((n_samples,max_len_x,neg_samples)).astype("int64")
    mid_mask = np.zeros((n_samples,max_len_x)).astype('float32')

    for idx, [s_x, s_y, no_sx, no_sy] in enumerate(zip(seqs_mid, seqs_cat, noclk_seqs_mid, noclk_seqs_cat)):
        mid_mask[idx, :lengths_x[idx]] = 1.
        mid_his[idx, :lengths_x[idx]] = s_x
        cat_his[idx, :lengths_x[idx]] = s_y
        noclk_mid_his[idx, :lengths_x[idx], :] = no_sx
        noclk_cat_his[idx, :lengths_x[idx], :] = no_sy

    uids = np.array([inp[0] for inp in input])
    mids = np.array([inp[1] for inp in input])
    cats = np.array([inp[2] for inp in input])

    if return_neg:
        return uids, mids, cats, mid_his, cat_his, mid_mask, np.array(target), np.array(lengths_x), noclk_mid_his, noclk_cat_his

    else:
        return uids, mids, cats, mid_his, cat_his, mid_mask, np.array(target), np.array(lengths_x)



def train(train_file = "data/local_train_splitByUser",
        test_file = "data/local_test_splitByUser",
        uid_voc = "data/uid_voc.pkl",
        mid_voc = "data/mid_voc.pkl",
        cat_voc = "data/cat_voc.pkl",
        batch_size = 128,
        maxlen = 100,
        test_iter = 100,
        save_iter = 100,
        model_type = 'DNN',
	    seed = 2,
    ):

    model_path = "dnn_save_path/ckpt_noshuff" + model_type + str(seed)
    best_model_path = "dnn_bast_model/ckpt_noshuff" + model_type + str(seed)
    gpu_options = tf.GPUOptions(allow_growth=True)
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
        train_data = DataIterator(train_file,uid_voc,mid_voc,cat_voc,batch_size,maxlen)
        test_data = DataIterator(test_file,uid_voc,mid_voc,cat_voc,batch_size,maxlen)

        n_uid,n_mid,n_cat = train_data.get_n()
        model = Model_DIN_V2_Gru_Vec_attGru_Neg(n_uid,n_mid,n_cat,EMBEDDING_DIM, HIDDEN_SIZE, ATTENTION_SIZE)

        sess.run(tf.global_variables_initializer())
        sess.run(tf.local_variables_initializer())
        iter = 0
        lr = 0.001
        for itr in range(3):
            loss_sum = 0.0
            accuracy_sum = 0.0
            aux_loss_sum = 0.0

            for src,tgt in train_data:
                uids, mids, cats, mid_his, cat_his, mid_mask, target, sl, noclk_mids, noclk_cats = prepare_data(src,tgt,maxlen,return_neg=True)
                loss, acc, aux_loss = model.train(sess, [uids, mids, cats, mid_his, cat_his, mid_mask, target, sl, lr,noclk_mids, noclk_cats])
                loss_sum += loss
                accuracy_sum += acc
                aux_loss_sum += aux_loss
                iter += 1
                if (iter % test_iter) == 0:
                    print('iter: %d ----> train_loss: %.8f ---- train_accuracy: %.4f ---- tran_aux_loss: %.4f' % \
                          (iter, loss_sum / test_iter, accuracy_sum / test_iter, aux_loss_sum / test_iter))
                    loss_sum = 0.0
                    accuracy_sum = 0.0
                    aux_loss_sum = 0.0
                if (iter % save_iter) == 0:
                    print('save model iter: %d' % (iter))
                    model.save(sess, model_path + "--" + str(iter))
            lr *= 0.5


if __name__ == '__main__':
    SEED = 5
    tf.set_random_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)
    train()