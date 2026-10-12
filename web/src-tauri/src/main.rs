// Application Mac : une fenêtre qui affiche le build Vite embarqué. Seule commande Rust :
// `enregistrer_csv`, qui écrit un export CSV là où l'utilisateur le choisit (boîte « Enregistrer
// sous »). Aucun accès générique au système de fichiers n'est exposé à l'interface.
use tauri_plugin_dialog::DialogExt;

/// Taille maximale d'un export (la France entière pèse quelques Mo).
const TAILLE_MAX: usize = 32 * 1024 * 1024;

/// Nom proposé : dernier élément, sans séparateur ni caractère de contrôle, suffixe `.csv`.
fn nom_propose(brut: &str) -> String {
    let base = brut.rsplit(['/', '\\']).next().unwrap_or("");
    let propre: String = base.chars().filter(|c| !c.is_control()).collect();
    let propre = propre.trim_matches('.').trim();
    let propre = if propre.is_empty() { "export" } else { propre };
    if propre.to_lowercase().ends_with(".csv") {
        propre.to_string()
    } else {
        format!("{propre}.csv")
    }
}

/// Ouvre « Enregistrer sous » et écrit `contenu` au chemin choisi. `Ok(false)` : annulé.
#[tauri::command]
async fn enregistrer_csv(
    app: tauri::AppHandle,
    nom_suggere: String,
    contenu: String,
) -> Result<bool, String> {
    if contenu.len() > TAILLE_MAX {
        return Err(format!("export trop volumineux ({} octets)", contenu.len()));
    }
    let Some(choix) = app
        .dialog()
        .file()
        .set_file_name(nom_propose(&nom_suggere))
        .add_filter("CSV", &["csv"])
        .blocking_save_file()
    else {
        return Ok(false);
    };
    let chemin = choix.into_path().map_err(|e| e.to_string())?;
    std::fs::write(&chemin, contenu).map_err(|e| format!("écriture impossible : {e}"))?;
    Ok(true)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![enregistrer_csv])
        .run(tauri::generate_context!())
        .expect("échec du démarrage de l'application");
}

#[cfg(test)]
mod tests {
    use super::nom_propose;

    #[test]
    fn nom_sans_chemin_ni_controle() {
        assert_eq!(nom_propose("../../etc/passwd"), "passwd.csv");
        assert_eq!(nom_propose("a\\b\\x.csv"), "x.csv");
        assert_eq!(nom_propose("ministere-info_scrutin_2022.csv"), "ministere-info_scrutin_2022.csv");
        assert_eq!(nom_propose("..."), "export.csv");
        assert_eq!(nom_propose("a\nb"), "ab.csv");
    }
}
