// Application Mac : une fenêtre qui affiche le build Vite embarqué. Seule commande Rust :
// `enregistrer_export`, qui écrit un export (.csv ou .xlsx) là où l'utilisateur le choisit
// (boîte « Enregistrer sous »). Aucun accès générique au système de fichiers n'est exposé.
use tauri::ipc::{InvokeBody, Request};
use tauri_plugin_dialog::DialogExt;

/// Taille maximale d'un export (la France entière pèse quelques Mo).
const TAILLE_MAX: usize = 32 * 1024 * 1024;
/// Extensions acceptées, seules.
const EXTENSIONS: [&str; 2] = ["csv", "xlsx"];

/// Nom proposé : dernier élément, sans séparateur ni caractère de contrôle ; extension `.csv`
/// ou `.xlsx` obligatoire (retournée en minuscules avec le nom).
fn nom_propose(brut: &str) -> Result<(String, &'static str), String> {
    let base = brut.rsplit(['/', '\\']).next().unwrap_or("");
    let propre: String = base.chars().filter(|c| !c.is_control()).collect();
    let propre = propre.trim_matches('.').trim().to_string();
    let ext = propre
        .rsplit_once('.')
        .map(|(_, e)| e.to_lowercase())
        .and_then(|e| EXTENSIONS.into_iter().find(|x| *x == e))
        .ok_or_else(|| "extension refusée (.csv ou .xlsx seulement)".to_string())?;
    Ok((propre, ext))
}

/// Ouvre « Enregistrer sous » et écrit les octets reçus (corps brut, nom dans l'en-tête `nom`)
/// au chemin choisi. `Ok(false)` : annulé.
#[tauri::command]
async fn enregistrer_export(app: tauri::AppHandle, requete: Request<'_>) -> Result<bool, String> {
    let InvokeBody::Raw(octets) = requete.body() else {
        return Err("corps binaire attendu".to_string());
    };
    if octets.len() > TAILLE_MAX {
        return Err(format!("export trop volumineux ({} octets)", octets.len()));
    }
    let brut = requete
        .headers()
        .get("nom")
        .and_then(|v| v.to_str().ok())
        .ok_or("nom de fichier absent")?;
    let (nom, ext) = nom_propose(brut)?;
    let Some(choix) = app
        .dialog()
        .file()
        .set_file_name(nom)
        .add_filter("Export", &[ext])
        .blocking_save_file()
    else {
        return Ok(false);
    };
    let mut chemin = choix.into_path().map_err(|e| e.to_string())?;
    let valide = chemin
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| EXTENSIONS.contains(&e.to_lowercase().as_str()));
    if !valide {
        chemin.set_extension(ext);
    }
    std::fs::write(&chemin, octets).map_err(|e| format!("écriture impossible : {e}"))?;
    Ok(true)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![enregistrer_export])
        .run(tauri::generate_context!())
        .expect("échec du démarrage de l'application");
}

#[cfg(test)]
mod tests {
    use super::nom_propose;

    #[test]
    fn nom_sans_chemin_ni_controle() {
        assert_eq!(nom_propose("../../etc/passwd.csv").unwrap(), ("passwd.csv".to_string(), "csv"));
        assert_eq!(nom_propose("a\\b\\x.XLSX").unwrap(), ("x.XLSX".to_string(), "xlsx"));
        assert_eq!(nom_propose("a\nb.csv").unwrap().0, "ab.csv");
    }

    #[test]
    fn extension_controlee() {
        for refuse in ["passwd", "x.sh", "x.csv.app", "...", "x.", ".csv.exe"] {
            assert!(nom_propose(refuse).is_err(), "{refuse}");
        }
    }
}
