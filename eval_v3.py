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
nodes = 3072
batch_size = 8
learning_rate_base = 0.0001
learning_rate_decay = 0.99
regularaztion_rate = 0.0001
training_steps = 30000
moving_average_decay = 0.99


def inference(input_tensor, train, regularizer):

    with tf.variable_scope('layer4-fc1',reuse=tf.AUTO_REUSE):
        fc1_weights = tf.get_variable("weights", [nodes, FC_SIZE],
                                          initializer=tf.truncated_normal_initializer(stddev=0.1))
        if regularizer != None:
            tf.add_to_collection('losses', regularizer(fc1_weights))
            pass
        fc1_biases = tf.get_variable("bias", [FC_SIZE], initializer=tf.constant_initializer(0.1))
        tf.summary.histogram('layer4-fc1-weights', fc1_weights)
        tf.summary.histogram('layer4-fc1-biases', fc1_biases)
        fc1 = tf.nn.relu(tf.matmul(input_tensor, fc1_weights) + fc1_biases)
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

x = tf.placeholder(tf.float32, [1, 48*64], name='x-input')
y_ = tf.placeholder(tf.float32, [1, 10], name='y-input')
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

cap = cv2.VideoCapture(0)

with tf.Session() as sess:
    module_file =  tf.train.latest_checkpoint('C://Users/lisixu/Desktop/YYG_Final/Our_trin_set/train3/')
    saver.restore(sess, module_file)
    while(1):
        data_temp = []
        ret, frame = cap.read()
        cv2.imshow("capture", frame)
        Grayimg = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        data = np.matrix(Grayimg)
        data = data.astype(np.float32)
        data = cv2.resize(data, (64,48), interpolation=cv2.INTER_AREA)
        data_temp.append(data)
        data_temp.append(data)
        data_temp = np.reshape(data_temp,(2,1,48*64))
        y_predict = sess.run([y],feed_dict={x: data_temp[0]})
        print(np.where(y_predict==np.max(y_predict)))
        #print("Current number:%d" % tf.argmax(y_predict))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break 
    cap.release()
    pass

