// Application Mac : une fenêtre qui affiche le build Vite embarqué ; aucune commande Rust.
fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("échec du démarrage de l'application");
}
