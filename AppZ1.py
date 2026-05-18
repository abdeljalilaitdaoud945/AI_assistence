import flet as ft 
from vues import home, mails, settings , AIassistant, rdv,calendrier
from services.google_auth import get_credentials, get_user_info

ROUTE_BUILDERS = {
    "/": home.build,
    "/mails": mails.build,
    "/rdv": rdv.build,
    "/settings": settings.build, 
    "/AI": AIassistant.build,
    "/calendrier": calendrier.build,
}


ROUTE_STACKS = {
    "/": ["/"],
    "/mails": ["/mails"],       
    "/rdv": ["/rdv"],           
    "/settings": ["/", "/settings"], 
    "/AI": ["/AI"],
    "/calendrier": ["/rdv","/calendrier"] 
}
def main(page: ft.Page):
    creds = get_credentials()           # JE MET CA EN COMMENTAIRE POUR METTRE LA CONNEXION GOOGLE EN PAUSE
    user= get_user_info(creds)                   # JE MET CA EN COMMENTAIRE POUR METTRE LA CONNEXION GOOGLE EN PAUSE
    print("Connecté :", creds.valid)
    print(f"Connecté : {user['prenom']} {user['nom']} ({user['email']})")
    page.data = user
    page.title = "INPT APP"
    page.fonts = {"PROSTO": "/fonts/ProstoOne-Regular.ttf"}
    
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.YELLOW,
        page_transitions=ft.PageTransitionsTheme(
            android=ft.PageTransitionTheme.NONE,
            ios=ft.PageTransitionTheme.NONE,
            macos=ft.PageTransitionTheme.NONE,
            linux=ft.PageTransitionTheme.NONE,
            windows=ft.PageTransitionTheme.NONE,
        )
    )

    # pour load les settings au début ajouter les nouveaux ici
    async def load_settings():
        # On doit utiliser await ici
        saved_theme = await page.shared_preferences.get("theme_mode")
        page.theme_mode = ft.ThemeMode.DARK if saved_theme == "dark" else ft.ThemeMode.LIGHT
        page.update()
            
    page.run_task(load_settings)

    page.current_tab = "/" 

    def route_change(e=None):
        page.views.clear()
        
        # On récupère la pile de routes à afficher
        stack = ROUTE_STACKS.get(page.route, ["/"])
        
        # On construit la pile
        for route_path in stack:
            if route_path in ROUTE_BUILDERS:
                page.views.append(ROUTE_BUILDERS[route_path](page))
        
        page.update()
        
    # ---pour retour en arriere
    async def view_pop(e):
        
        if page.route == "/settings":
            await page.push_route(page.current_tab)
        else:
            # Sinon on retourne à l'accueil par défaut
            await page.push_route("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    route_change()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)