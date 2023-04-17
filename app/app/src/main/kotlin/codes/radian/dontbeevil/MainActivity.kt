package codes.radian.dontbeevil

import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle

import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.NavigationUI
import com.google.android.material.bottomnavigation.BottomNavigationView

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val navHostFragment =
            supportFragmentManager.findFragmentById(R.id.navbar_fragment) as NavHostFragment
        val navController = navHostFragment.navController
        val navbar = findViewById<BottomNavigationView>(R.id.navbar)

        NavigationUI.setupWithNavController(navbar, navController)

        navbar.setOnItemSelectedListener {
            NavigationUI.onNavDestinationSelected(it, navController)
        }
    }
}
