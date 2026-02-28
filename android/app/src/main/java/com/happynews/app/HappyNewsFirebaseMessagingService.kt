package com.happynews.app

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class HappyNewsFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        // M4で実装
    }
    override fun onNewToken(token: String) {
        // M4で実装
    }
}
