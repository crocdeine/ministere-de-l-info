// Seule commande exposée à l'interface : `enregistrer_export` (permission `allow-enregistrer-export`).
fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new()
            .app_manifest(tauri_build::AppManifest::new().commands(&["enregistrer_export"])),
    )
    .expect("échec de la préparation de l'application");
}
