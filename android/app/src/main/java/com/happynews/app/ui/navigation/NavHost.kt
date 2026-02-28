package com.happynews.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.happynews.app.ui.bookmarks.BookmarksScreen
import com.happynews.app.ui.detail.DetailScreen
import com.happynews.app.ui.legal.LegalScreen
import com.happynews.app.ui.settings.NotificationSettingsScreen
import com.happynews.app.ui.settings.SettingsScreen
import com.happynews.app.ui.today.TodayScreen

sealed class Screen(val route: String) {
    object Today : Screen("today")
    object Bookmarks : Screen("bookmarks")
    object Settings : Screen("settings")
    object NotificationSettings : Screen("notification_settings")
    object Legal : Screen("legal")
    object Detail : Screen("detail/{articleId}") {
        fun createRoute(id: String) = "detail/$id"
    }
}

@Composable
fun HappyNewsNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Screen.Today.route) {
        composable(Screen.Today.route) {
            TodayScreen(onArticleClick = { id ->
                navController.navigate(Screen.Detail.createRoute(id))
            })
        }
        composable(
            route = Screen.Detail.route,
            arguments = listOf(navArgument("articleId") { type = NavType.StringType }),
        ) {
            DetailScreen(onBack = { navController.popBackStack() })
        }
        composable(Screen.Bookmarks.route) {
            BookmarksScreen(onArticleClick = { id ->
                navController.navigate(Screen.Detail.createRoute(id))
            })
        }
        composable(Screen.Settings.route) {
            SettingsScreen(
                onNotificationClick = { navController.navigate(Screen.NotificationSettings.route) },
                onLegalClick = { navController.navigate(Screen.Legal.route) },
            )
        }
        composable(Screen.NotificationSettings.route) {
            NotificationSettingsScreen(onBack = { navController.popBackStack() })
        }
        composable(Screen.Legal.route) {
            LegalScreen()
        }
    }
}
