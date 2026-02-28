package com.happynews.app.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.happynews.app.data.repository.SettingsRepository
import com.happynews.app.domain.model.UserSettings
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class NotificationSettingsViewModel @Inject constructor(
    private val repository: SettingsRepository,
) : ViewModel() {

    val settings: StateFlow<UserSettings> = repository.settings
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), UserSettings())

    fun setNotificationEnabled(enabled: Boolean) {
        viewModelScope.launch { repository.updateNotificationEnabled(enabled) }
    }

    fun setNotificationHour(hour: Int) {
        viewModelScope.launch { repository.updateNotificationHour(hour) }
    }
}
