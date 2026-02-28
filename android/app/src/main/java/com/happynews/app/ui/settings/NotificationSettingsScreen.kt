package com.happynews.app.ui.settings

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ListItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationSettingsScreen(
    viewModel: NotificationSettingsViewModel = hiltViewModel(),
    onBack: () -> Unit,
) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var expanded by remember { mutableStateOf(false) }

    Scaffold(topBar = { TopAppBar(title = { Text("通知設定") }) }) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .verticalScroll(rememberScrollState()),
        ) {
            // 通知 ON/OFF
            ListItem(
                headlineContent = { Text("通知") },
                supportingContent = { Text("毎日ハッピーニュースをお届け") },
                trailingContent = {
                    Switch(
                        checked = settings.notificationEnabled,
                        onCheckedChange = { viewModel.setNotificationEnabled(it) },
                    )
                },
            )
            HorizontalDivider()

            // 時刻選択（HH:00）
            if (settings.notificationEnabled) {
                ListItem(
                    headlineContent = {
                        ExposedDropdownMenuBox(
                            expanded = expanded,
                            onExpandedChange = { expanded = !expanded },
                        ) {
                            OutlinedTextField(
                                value = "${settings.notificationHour}:00",
                                onValueChange = {},
                                readOnly = true,
                                label = { Text("通知時刻") },
                                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                                modifier = Modifier.menuAnchor(),
                            )
                            ExposedDropdownMenu(
                                expanded = expanded,
                                onDismissRequest = { expanded = false },
                            ) {
                                (0..23).forEach { hour ->
                                    DropdownMenuItem(
                                        text = { Text("${hour}:00") },
                                        onClick = {
                                            viewModel.setNotificationHour(hour)
                                            expanded = false
                                        },
                                    )
                                }
                            }
                        }
                    },
                )
                HorizontalDivider()
            }

            // OS設定誘導
            ListItem(
                headlineContent = { Text("OS通知設定を開く") },
                supportingContent = { Text("通知が届かない場合はここから設定") },
                trailingContent = {
                    TextButton(onClick = {
                        context.startActivity(
                            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                                putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                            }
                        )
                    }) { Text("開く") }
                },
            )
        }
    }
}
