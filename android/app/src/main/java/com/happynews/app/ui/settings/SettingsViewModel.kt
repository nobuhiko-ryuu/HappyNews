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
class SettingsViewModel @Inject constructor(
    private val repository: SettingsRepository,
) : ViewModel() {

    val settings: StateFlow<UserSettings> = repository.settings
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), UserSettings())

    fun addMuteWord(word: String) {
        if (word.isBlank()) return
        viewModelScope.launch { repository.addMuteWord(word.trim()) }
    }

    fun removeMuteWord(word: String) {
        viewModelScope.launch { repository.removeMuteWord(word) }
    }
}
