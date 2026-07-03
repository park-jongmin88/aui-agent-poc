"""TensorFlow/Keras 분류 — Sequential 모델 + 내장 MNIST → .keras 저장.
가장 전형적인 Keras 형태.
"""
import tensorflow as tf

def main():
    (x_tr, y_tr), (x_te, y_te) = tf.keras.datasets.mnist.load_data()
    x_tr, x_te = x_tr / 255.0, x_te / 255.0

    model = tf.keras.Sequential([
        tf.keras.layers.Flatten(input_shape=(28, 28)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    model.compile(optimizer="adam",
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    model.fit(x_tr, y_tr, epochs=1, batch_size=128, verbose=1)
    print("test:", model.evaluate(x_te, y_te, verbose=0))

    model.save("model.keras")
    print("saved: model.keras")

if __name__ == "__main__":
    main()
