package com.happynews.app.util

import android.util.Log
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

/**
 * AD-022: 通信量ガードログ
 * 画像ロード数・推定バイト数を記録し、超過時に警告する。
 */
object ImageSizeLogger {
    private const val TAG = "ImageSizeLogger"
    private const val WARN_BYTES_PER_DAY = 1_000_000L  // 1MB/日目標

    private val loadCount = AtomicInteger(0)
    private val totalBytes = AtomicLong(0L)

    fun recordImageLoad(estimatedBytes: Long) {
        val count = loadCount.incrementAndGet()
        val total = totalBytes.addAndGet(estimatedBytes)
        if (total > WARN_BYTES_PER_DAY) {
            Log.w(TAG, "Image traffic warning: ${total / 1024}KB loaded ($count images). Exceeds 1MB/day target.")
        } else {
            Log.d(TAG, "Image load #$count: +${estimatedBytes / 1024}KB, total=${total / 1024}KB")
        }
    }

    fun reset() {
        loadCount.set(0)
        totalBytes.set(0L)
    }

    fun summary(): String {
        return "Images: ${loadCount.get()} loaded, ${totalBytes.get() / 1024}KB total"
    }
}
