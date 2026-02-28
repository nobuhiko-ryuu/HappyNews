package com.happynews.app.data.repository

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.happynews.app.data.api.HappyNewsApi
import com.happynews.app.data.api.model.SettingsRequest
import com.happynews.app.domain.model.UserSettings
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

val Context.dataStore by preferencesDataStore(name = "settings")

@Singleton
class SettingsRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val api: HappyNewsApi,
) {
    private val notifEnabled = booleanPreferencesKey("notification_enabled")
    private val notifHour = intPreferencesKey("notification_hour")
    private val muteWordsKey = stringPreferencesKey("mute_words")

    val settings: Flow<UserSettings> = context.dataStore.data.map { prefs ->
        UserSettings(
            notificationEnabled = prefs[notifEnabled] ?: false,
            notificationHour = prefs[notifHour] ?: 8,
            muteWords = prefs[muteWordsKey]?.split(",")?.filter { it.isNotEmpty() } ?: emptyList(),
        )
    }

    suspend fun updateNotificationEnabled(enabled: Boolean) {
        context.dataStore.edit { it[notifEnabled] = enabled }
        try { api.updateSettings(SettingsRequest(notificationEnabled = enabled)) } catch (_: Exception) {}
    }

    suspend fun updateNotificationHour(hour: Int) {
        context.dataStore.edit { it[notifHour] = hour }
        try { api.updateSettings(SettingsRequest(notificationTime = hour)) } catch (_: Exception) {}
    }

    suspend fun addMuteWord(word: String) {
        context.dataStore.edit { prefs ->
            val current = prefs[muteWordsKey]?.split(",")?.filter { it.isNotEmpty() } ?: emptyList()
            prefs[muteWordsKey] = (current + word).joinToString(",")
        }
        val current = settings
        try {
            val words = context.dataStore.data.map { prefs ->
                prefs[muteWordsKey]?.split(",")?.filter { it.isNotEmpty() } ?: emptyList()
            }
            // API同期はベストエフォート
        } catch (_: Exception) {}
    }

    suspend fun removeMuteWord(word: String) {
        context.dataStore.edit { prefs ->
            val current = prefs[muteWordsKey]?.split(",")?.filter { it.isNotEmpty() } ?: emptyList()
            prefs[muteWordsKey] = current.filter { it != word }.joinToString(",")
        }
    }
}
