package com.happynews.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.happynews.app.ui.detail.DetailScreen
import com.happynews.app.ui.today.TodayScreen

sealed class Screen(val route: String) {
    object Today : Screen("today")
    object Detail : Screen("detail/{articleId}") {
        fun createRoute(id: String) = "detail/$id"
    }
}

@Composable
fun HappyNewsNavHost() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = Screen.Today.route) {
        composable(Screen.Today.route) {
            TodayScreen(onArticleClick = { id ->
                navController.navigate(Screen.Detail.createRoute(id))
            })
        }
        composable(
            route = Screen.Detail.route,
            arguments = listOf(navArgument("articleId") { type = NavType.StringType })
        ) {
            DetailScreen(onBack = { navController.popBackStack() })
        }
    }
}
