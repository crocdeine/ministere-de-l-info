// Seule commande exposée à l'interface : `enregistrer_csv` (permission `allow-enregistrer-csv`).
fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new()
            .app_manifest(tauri_build::AppManifest::new().commands(&["enregistrer_csv"])),
    )
    .expect("échec de la préparation de l'application");
}
