use std::collections::HashMap;
use std::fs;
use std::fs::File;
use std::io::Write;
use std::path::Path;

use serde::{Deserialize, Serialize}; // Import the traits

pub mod address;
pub mod pdb_store;
pub mod utils;

fn default_version() -> String {
    "".into()
}

fn default_file_info() -> FileInfo {
    FileInfo{
        size: 0,
        virtualSize: 0,
        timestamp: 0,
        version: "".into(),
    }
}


// --- 1. Define the necessary data structures for deserialization ---

// The deepest nested structure we need.
#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct FileInfo {
    size: u64,
    virtualSize: u64,
    timestamp: u64,
    #[serde(default = "default_version")]
    version: String, // e.g., "10.0.10240.17914 (th1.180627-1911)"
}

// The structure holding FileInfo and the deeply nested Windows version information.
// We only need the outermost map key (the SHA256 hash) and the internal data.
#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct RecordData {
    #[serde(default = "default_file_info")]
    file_info: FileInfo,
    windows_versions: HashMap<String, HashMap<String, Kbs>>,
}

// Struct for the KB update, contains the assembly information.
#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct Kbs {
    // assemblies: HashMap<String, Assembly>,
    // We don't need the updateInfo field for this task, but it must be included
    // or ignored if present. Since we ignore it below, we omit it here for simplicity.
}

// Struct for the Assembly information.
#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct Assembly {
    attributes: Vec<Attribute>,
}

// Struct for the Attribute, which contains the filename we need.
#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct Attribute {
    #[serde(rename = "sourceName")]
    source_name: String, // This is the PE filename, e.g., "ntkrnlmp.exe"
    #[serde(rename = "name")]
    destination_name: String, // This is the target filename, e.g., "ntoskrnl.exe"
}


fn generate_download_url(timestamp: u64, size: u64, pe_name: &str) -> String {
    // 1. Generate the fileId part

    // Timestamp part (8 hex digits, uppercase)
    let time_hex = format!("{:08X}", timestamp);

    // Size part (hex, lowercase)
    let size_hex = format!("{:x}", size);

    let file_id = format!("{}{}", time_hex, size_hex);

    // 2. Construct the final URL
    format!(
        "https://msdl.microsoft.com/download/symbols/{}/{}/{}",
        pe_name,
        file_id,
        pe_name
    )
}

/// Downloads a file from a URL and saves it to a specified path.
fn download_file(url: &str, target_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    println!("Downloading from: {}", url);

    // Make a blocking GET request
    let response = reqwest::blocking::get(url)?;

    if !response.status().is_success() {
        return Err(format!("Failed to download file. Status: {}", response.status()).into());
    }

    // Ensure the parent directory exists
    if let Some(parent) = target_path.parent() {
        fs::create_dir_all(parent)?;
    }

    // Save the file
    let mut file = fs::File::create(target_path)?;
    file.write_all(&response.bytes()?)?;

    println!("Successfully downloaded and saved to: {}", target_path.display());

    Ok(())
}

fn process_entry(sha256_hash: &String, record: &RecordData) -> Result<pdb_store::PdbStore, Box<dyn std::error::Error>> {
    println!("Processing record for SHA256: {}", sha256_hash);

    // --- 4. Extract required fields ---
    let timestamp = record.file_info.timestamp;
    let size = record.file_info.virtualSize;

    // Extract the core version number (e.g., "10.0.10240.17914")
    let version = record.file_info.version.split_whitespace().next().unwrap_or("unknown");

    let pe_name = "ntoskrnl.exe";
    // The target filename is what you specified in the path: ntoskrnl.exe
    let target_filename = "ntoskrnl.exe";

    println!("- Timestamp: {}", timestamp);
    println!("- File Size: {}", size);
    println!("- Version: {}", version);
    println!("- PE Name (used for URL): {}", pe_name);

    // --- 5. Generate the URL and target path ---
    let download_url = generate_download_url(timestamp, size, pe_name);

    // Target path: files/<version>/ntoskrnl.exe
    let target_path = Path::new("files").join(version).join(target_filename);

    println!("- Download URL: {}", download_url);
    println!("- Target Path: {}", target_path.display());

    download_file(&download_url, &target_path)?;

    let pdb_store = pdb_store::parse_pdb(&target_path)?;
    // println!("pdb store symbols {:?}\n", pdb_store.symbols);
    // println!("pdb store structs {:?}\n", pdb_store.structs);
    Ok(pdb_store)
}


struct Version{
    codename: String,
    version: String,
}

fn get_os_version(record: &RecordData) -> Option<Version> {
    let os_versions = vec![
        Version{
            codename: "Windows 11 24H2".into(),
            version: "10.0.26100".into()
        },
        Version{
            codename: "Windows 11 23H2".into(),
            version: "10.0.22631".into()
        },
        Version{
            codename: "Windows 11 22H2".into(),
            version: "10.0.22621".into()
        },
        Version{
            codename: "Windows 11 21H2".into(),
            version: "10.0.22000".into()
        },
        Version{
            codename: "Windows 10 22H2".into(),
            version: "10.0.19045".into()
        },
        // Version{
        //     codename: "Windows 10 21H2",
        //     version: "10.0.19044"
        // },
        // Version{
        //     codename: "Windows 10 20H2",
        //     version: "10.0.19042"
        // },
        // Version{
        //     codename: "Windows 10 2004",
        //     version: "10.0.19041"
        // },
        // Version{
        //     codename: "Windows 10 1909",
        //     version: "10.0.18363"
        // },
        // Version{
        //     codename: "Windows 10 1809",
        //     version: "10.0.17763"
        // },
        // Version{
        //     codename: "Windows 10 1709",
        //     version: "10.0.16299"
        // },
        // Version{
        //     codename: "Windows 10 1609",
        //     version: "10.0.14393"
        // },
        // Version{
        //     codename: "Windows 10 1509",
        //     version: "10.0.10240"
        // },
    ];
    let version = record.file_info.version.split_whitespace().next().unwrap_or("unknown");
    for os in os_versions.into_iter() {
        if version.starts_with(&os.version) {
            return Some(os);
        }
    }
    return None;
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let file = File::open("ntoskrnl.exe.json")?;
    // let file = File::open("test.json")?;

    let records: HashMap<String, RecordData> = serde_json::from_reader(file)?;

    let mut i = 100;
    for (sha256_hash, record) in records.into_iter() {
        let os_version = get_os_version(&record);
        if os_version.is_none() {
            continue;
        }

        let os_version = os_version.unwrap();
        if let Ok(store) = process_entry(&sha256_hash, &record) {
            let version = record.file_info.version.split_whitespace().next().unwrap_or("unknown");
            let info_file = Path::new("files").join(version).join("info.txt");

            let mut file = File::create(info_file).expect("Failed to create file");
            writeln!(&mut file, "{} - {}", os_version.codename, version);
            store.print_default_information(&mut file);
        }

        i-=1;
        if (i == 0) {
            break;
        }
    }

    Ok(())
}
