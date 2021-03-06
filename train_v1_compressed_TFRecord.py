#conv1 conv2 pool fc1 fc2
from PIL import Image
import numpy  as np
import tensorflow as tf
import cv2 
import time

NUM_CHANNELS = 1
NUM_LABELS = 10

CONV1_DEEP = 32
CONV1_SIZE = 3
CONV2_DEEP = 32
CONV2_SIZE = 3
FC_SIZE = 128

batch_size = 8
learning_rate_base = 0.0001
learning_rate_decay = 0.99
regularaztion_rate = 0.0001
training_steps = 30000
moving_average_decay = 0.99

print('-' * 30)
print('Loading train data and Initlizing CNN Network')
print('-' * 30)

filename_queue = tf.train.string_input_producer([r'C:\Users\lisixu\Desktop\project_rebulid\train.tfrecords'])
reader = tf.TFRecordReader()
_,serialized_example = reader.read(filename_queue)
features = tf.parse_single_example(serialized_example,
                                    features ={
                                        'label': tf.FixedLenFeature([10], tf.int64),
                                        'image':tf.FixedLenFeature([],tf.string)
                                    })
img = tf.decode_raw(features['image'],tf.uint8)
img = tf.reshape(img,[3072])
img = tf.cast(img,tf.float32)*(1.0/255.0)
label = tf.cast(features['label'],tf.float32)
img_batch,label_batch  = tf.train.shuffle_batch([img,label],batch_size=batch_size,capacity= 216,min_after_dequeue=200)

def inference(input_tensor, train, regularizer):
    with tf.variable_scope('layer1-conv1',reuse=tf.AUTO_REUSE):
        conv1_weights = tf.get_variable("weight", [CONV1_SIZE, CONV1_SIZE, NUM_CHANNELS, CONV1_DEEP],
                                        initializer=tf.truncated_normal_initializer(stddev=0.1))
        conv1_biases = tf.get_variable("bias", [CONV1_DEEP], initializer=tf.constant_initializer(0.0))
        tf.summary.histogram('layer1-conv1-weights', conv1_weights)
        tf.summary.histogram('layer1-conv1-biases', conv1_biases)

        conv1 = tf.nn.conv2d(input_tensor, conv1_weights, strides=[1, 1, 1, 1], padding='SAME')
        relu1 = tf.nn.relu(tf.nn.bias_add(conv1, conv1_biases))
        pass

    with tf.variable_scope('layer2-conv2',reuse=tf.AUTO_REUSE):
        conv2_weights = tf.get_variable("weight", [CONV2_SIZE, CONV2_SIZE, CONV1_DEEP, CONV2_DEEP],
                                        initializer=tf.truncated_normal_initializer(stddev=0.1))
        conv2_biases = tf.get_variable("bias", [CONV2_DEEP], initializer=tf.constant_initializer(0.0))
        tf.summary.histogram('layer2-conv2-weights', conv2_weights)
        tf.summary.histogram('layer2-conv2-biases', conv2_biases)

        conv2 = tf.nn.conv2d(relu1, conv2_weights, strides=[1, 1, 1, 1], padding='SAME')
        relu2 = tf.nn.relu(tf.nn.bias_add(conv2, conv2_biases))
        pass

    with tf.variable_scope('layer3-pool'):
        pool = tf.nn.max_pool(relu2, ksize=[1, 2, 2, 1], strides=[1, 1, 1, 1], padding='SAME')
        pass
    
    pool_shape = pool.get_shape().as_list()
    nodes = pool_shape[1] * pool_shape[2] * pool_shape[3]
    reshaped = tf.reshape(pool, [pool_shape[0], nodes])

    with tf.variable_scope('layer4-fc1',reuse=tf.AUTO_REUSE):
        fc1_weights = tf.get_variable("weights", [nodes, FC_SIZE],
                                          initializer=tf.truncated_normal_initializer(stddev=0.1))
        if regularizer != None:
            tf.add_to_collection('losses', regularizer(fc1_weights))
            pass
        fc1_biases = tf.get_variable("bias", [FC_SIZE], initializer=tf.constant_initializer(0.1))
        tf.summary.histogram('layer4-fc1-weights', fc1_weights)
        tf.summary.histogram('layer4-fc1-biases', fc1_biases)
        fc1 = tf.nn.relu(tf.matmul(reshaped, fc1_weights) + fc1_biases)
        if train: fc1 = tf.nn.dropout(fc1, 0.5)
        pass

    with tf.variable_scope('layer4-fc2',reuse=tf.AUTO_REUSE):
        fc2_weights = tf.get_variable("weights", [FC_SIZE, NUM_LABELS],
                                          initializer=tf.truncated_normal_initializer(stddev=0.1))
        if regularizer != None:
            tf.add_to_collection('losses', regularizer(fc2_weights))
            pass
        fc2_biases = tf.get_variable("bias", [NUM_LABELS], initializer=tf.constant_initializer(0.1))
        tf.summary.histogram('layer4-fc2-weights', fc2_weights)
        tf.summary.histogram('layer4-fc2-biases', fc2_biases)
        logit = tf.matmul(fc1, fc2_weights) + fc2_biases
        pass

    return logit

x = tf.placeholder(tf.float32, [8, 48, 64,1], name='x-input')
y_ = tf.placeholder(tf.float32, [8, 10], name='y-input')
regularizer = tf.contrib.layers.l2_regularizer(regularaztion_rate)
y = inference(x, train=True, regularizer=regularizer)
global_step = tf.Variable(0, trainable=False)
variable_averages = tf.train.ExponentialMovingAverage(moving_average_decay, global_step)
variable_averages_op = variable_averages.apply(tf.trainable_variables())
cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=y, labels=tf.argmax(y_, 1))
cross_entropy_mean = tf.reduce_mean(cross_entropy)
loss = cross_entropy_mean + tf.add_n(tf.get_collection('losses'))
tf.summary.scalar('cross_entropy_mean', cross_entropy_mean)
tf.summary.scalar('loss', loss)
learning_rate = tf.train.exponential_decay(learning_rate_base, global_step, 125, learning_rate_decay)
tf.summary.scalar('learning_rate', learning_rate)
train_step = tf.train.AdamOptimizer(learning_rate).minimize(loss, global_step=global_step)
correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(y_, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
tf.summary.scalar('accuracy', accuracy)

with tf.control_dependencies([train_step, variable_averages_op]):
    train_op = tf.no_op(name='train')
    pass
saver = tf.train.Saver()
merged = tf.summary.merge_all()


with tf.Session() as sess:
    init_op = tf.global_variables_initializer()
    sess.run(init_op)
    train_writer = tf.summary.FileWriter('train', sess.graph)
    for i in range(training_steps):
        xs,ys = sess.run([img_batch,label_batch])
        xs = tf.reshape(xs,(8,48,64,1))
        ys = tf.reshape(ys,(8,10))
        _, loss_value, step, summary, accuracy_count = sess.run([train_op, loss, global_step, merged,accuracy],
                                                        feed_dict={x: xs, y_: ys})
        print("After %d training step(s), loss on training batch is %g,accuracy on training batch is %g" % (step, loss_value,accuracy_count))
        saver.save(sess, "train/savesample.ckpt", global_step=global_step)
        train_writer.add_summary(summary, i)
        train_writer.flush()
        pass
    train_writer.close()
    pass


