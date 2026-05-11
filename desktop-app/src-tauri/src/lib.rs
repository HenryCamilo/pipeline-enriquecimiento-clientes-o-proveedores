use std::fs;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

// ── Pipeline running guard ────────────────────────────────────────────────────

static PIPELINE_RUNNING: AtomicBool = AtomicBool::new(false);

// ── Shared structs ────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PipelineConfig {
    pub excel_path: String,
    pub documents_path: String,
    pub output_path: String,
    pub execution_mode: String,
    pub parallel_workers: u32,
    pub cache_enabled: bool,
    pub use_gpt: bool,
    pub max_gpt_doc_ratio: f64,
    pub column_mapping: serde_json::Value,
    pub sheet_name: serde_json::Value,
    pub header_row: u32,
    pub export_mode: String,
    pub python_path: Option<String>,
    pub backend_path: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct MappingProfile {
    pub name: String,
    pub description: String,
    pub mapping: serde_json::Value,
    pub sheet_name: serde_json::Value,
    pub header_row: u32,
    pub export_mode: String,
}

// ── File / folder selection commands ─────────────────────────────────────────

#[tauri::command]
async fn select_excel_file(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let result = tauri::async_runtime::spawn_blocking(move || {
        app.dialog()
            .file()
            .add_filter("Excel", &["xlsx", "xls"])
            .blocking_pick_file()
    })
    .await
    .map_err(|e| e.to_string())?;
    Ok(result.map(|p| p.to_string()))
}

#[tauri::command]
async fn select_folder(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let result = tauri::async_runtime::spawn_blocking(move || {
        app.dialog().file().blocking_pick_folder()
    })
    .await
    .map_err(|e| e.to_string())?;
    Ok(result.map(|p| p.to_string()))
}

// ── Pipeline execution command ────────────────────────────────────────────────

#[tauri::command]
async fn start_pipeline(app: AppHandle, config: PipelineConfig) -> Result<(), String> {
    if PIPELINE_RUNNING.swap(true, Ordering::SeqCst) {
        return Err("El pipeline ya está en ejecución. Espera a que termine.".to_string());
    }

    let config_json = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    let config_path = std::env::temp_dir().join("act_proveedores_config.json");
    fs::write(&config_path, &config_json)
        .map_err(|e| format!("No se pudo escribir config temporal: {}", e))?;

    let python_path = config.python_path.clone().unwrap_or_else(|| "python".to_string());
    let backend_path = config.backend_path.clone().unwrap_or_else(|| ".".to_string());
    let config_path_str = config_path.to_string_lossy().to_string();
    let app_clone = app.clone();

    tauri::async_runtime::spawn_blocking(move || {
        let result = run_python_pipeline(&app_clone, &python_path, &backend_path, &config_path_str);
        PIPELINE_RUNNING.store(false, Ordering::SeqCst);
        if let Err(err) = result {
            let _ = app_clone.emit("pipeline-error", serde_json::json!({ "error": err }));
        }
    });

    Ok(())
}

// ── Column detection command ──────────────────────────────────────────────────

/// Runs `python -m src.schema.column_detector --excel <path> …` and returns JSON.
#[tauri::command]
async fn detect_excel_columns(
    excel_path: String,
    python_path: String,
    backend_path: String,
    sheet_name: String,
    header_row: u32,
) -> Result<serde_json::Value, String> {
    let parts: Vec<&str> = python_path.splitn(2, ' ').collect();
    let program = parts[0].to_string();
    let prefix_args: Vec<String> = if parts.len() > 1 {
        parts[1].split_whitespace().map(String::from).collect()
    } else {
        vec![]
    };

    let program_c = program.clone();
    let prefix_c = prefix_args.clone();
    let excel_c = excel_path.clone();
    let backend_c = backend_path.clone();
    let sheet_c = sheet_name.clone();

    let output = tauri::async_runtime::spawn_blocking(move || {
        Command::new(&program_c)
            .args(&prefix_c)
            .args([
                "-m", "src.schema.column_detector",
                "--excel", &excel_c,
                "--sheet", &sheet_c,
                "--header-row", &header_row.to_string(),
            ])
            .current_dir(&backend_c)
            .output()
    })
    .await
    .map_err(|e| e.to_string())?
    .map_err(|e| format!("No se pudo ejecutar Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(format!("Python error: {}", stderr));
    }

    serde_json::from_str(&stdout)
        .map_err(|e| format!("No se pudo parsear la respuesta de Python: {} — salida: {}", e, stdout))
}

// ── Mapping profile commands ──────────────────────────────────────────────────

#[tauri::command]
async fn list_mapping_profiles(profiles_dir: String) -> Result<Vec<MappingProfile>, String> {
    let dir = Path::new(&profiles_dir);
    if !dir.exists() {
        return Ok(vec![]);
    }

    let mut profiles = vec![];
    let entries = fs::read_dir(dir).map_err(|e| e.to_string())?;

    for entry in entries.flatten() {
        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        if !matches!(ext, "yaml" | "yml" | "json") {
            continue;
        }
        match load_profile_from_path(&path) {
            Ok(p) => profiles.push(p),
            Err(_) => continue,
        }
    }

    profiles.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(profiles)
}

#[tauri::command]
async fn load_mapping_profile(profile_path: String) -> Result<MappingProfile, String> {
    load_profile_from_path(Path::new(&profile_path))
}

#[tauri::command]
async fn save_mapping_profile(
    profile: MappingProfile,
    profiles_dir: String,
) -> Result<String, String> {
    let dir = Path::new(&profiles_dir);
    fs::create_dir_all(dir).map_err(|e| e.to_string())?;

    let stem = safe_stem(&profile.name);
    let path = dir.join(format!("{}.json", stem));

    let content = serde_json::to_string_pretty(&profile).map_err(|e| e.to_string())?;
    fs::write(&path, content).map_err(|e| e.to_string())?;

    Ok(path.to_string_lossy().to_string())
}

// ── Open path command ─────────────────────────────────────────────────────────

#[tauri::command]
async fn open_path(path: String) -> Result<(), String> {
    open_in_os(&path)
}

// ── Internal helpers ──────────────────────────────────────────────────────────

fn run_python_pipeline(
    app: &AppHandle,
    python_path: &str,
    backend_path: &str,
    config_path: &str,
) -> Result<(), String> {
    let parts: Vec<&str> = python_path.splitn(2, ' ').collect();
    let program = parts[0];
    let prefix_args: Vec<&str> = if parts.len() > 1 {
        parts[1].split_whitespace().collect()
    } else {
        vec![]
    };

    let mut child = Command::new(program)
        .args(&prefix_args)
        .args(["-m", "src.main", "--config", config_path, "--json-logs"])
        .current_dir(backend_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("No se pudo iniciar Python ('{}') en '{}': {}", python_path, backend_path, e))?;

    let stdout = child.stdout.take().expect("stdout");
    let stderr = child.stderr.take().expect("stderr");

    let app_out = app.clone();
    let t1 = std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            let Ok(line) = line else { break };
            let trimmed = line.trim().to_string();
            if trimmed.is_empty() { continue; }
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(&trimmed) {
                let _ = app_out.emit("pipeline-event", v);
            } else {
                let _ = app_out.emit("pipeline-log", serde_json::json!({ "level": "info", "message": trimmed }));
            }
        }
    });

    let app_err = app.clone();
    let t2 = std::thread::spawn(move || {
        for line in BufReader::new(stderr).lines() {
            let Ok(line) = line else { break };
            let trimmed = line.trim().to_string();
            if !trimmed.is_empty() {
                let _ = app_err.emit("pipeline-log", serde_json::json!({ "level": "error", "message": trimmed }));
            }
        }
    });

    let _ = t1.join();
    let _ = t2.join();

    let status = child.wait().map_err(|e| e.to_string())?;
    let _ = app.emit("pipeline-process-exit", serde_json::json!({
        "success": status.success(),
        "code": status.code()
    }));

    Ok(())
}

fn load_profile_from_path(path: &Path) -> Result<MappingProfile, String> {
    let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

    let value: serde_json::Value = if matches!(ext, "yaml" | "yml") {
        serde_yaml::from_str(&content).map_err(|e| e.to_string())?
    } else {
        serde_json::from_str(&content).map_err(|e| e.to_string())?
    };

    let name = value["name"].as_str().unwrap_or(
        path.file_stem().and_then(|s| s.to_str()).unwrap_or("profile")
    ).to_string();

    Ok(MappingProfile {
        name,
        description: value["description"].as_str().unwrap_or("").to_string(),
        mapping: value["mapping"].clone(),
        sheet_name: value.get("sheet_name").cloned().unwrap_or(serde_json::json!(0)),
        header_row: value["header_row"].as_u64().unwrap_or(0) as u32,
        export_mode: value["export_mode"].as_str().unwrap_or("original").to_string(),
    })
}

fn open_in_os(path: &str) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd").args(["/C", "start", "", path]).spawn().map_err(|e| e.to_string())?;
        return Ok(());
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open").arg(path).spawn().map_err(|e| e.to_string())?;
        return Ok(());
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open").arg(path).spawn().map_err(|e| e.to_string())?;
        return Ok(());
    }
    #[allow(unreachable_code)]
    Err("Plataforma no soportada".to_string())
}

fn safe_stem(name: &str) -> String {
    let s: String = name.chars()
        .map(|c| if c.is_alphanumeric() || c == '-' { c } else { '_' })
        .collect();
    let s = s.to_lowercase();
    if s.is_empty() { "profile".to_string() } else { s.chars().take(64).collect() }
}

// ── Entry point ───────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            select_excel_file,
            select_folder,
            start_pipeline,
            detect_excel_columns,
            list_mapping_profiles,
            load_mapping_profile,
            save_mapping_profile,
            open_path,
        ])
        .run(tauri::generate_context!())
        .expect("Error iniciando la aplicación Tauri");
}
