//! Provides miscellaneous utilities.

/// Splits a database header key into base path and database header file name.
///
/// The first item in the returned value is the base path and the second item is
/// the database header file name.
/// The path is separated by a slash (`/`).
///
/// Fails if:
/// - `key` does not contain a slash (`/`)
/// - base path is empty
/// - database header file name is empty
pub fn split_database_header_key<'a>(
    key: &'a str,
) -> Result<(&'a str, &'a str), anyhow::Error> {
    let parts: Vec<&'a str> = key.rsplitn(2, '/').collect();
    if parts.len() != 2 {
        anyhow::bail!("key does not contain a slash")
    }
    if parts[1].is_empty() {
        anyhow::bail!("key does not have a base path");
    }
    if parts[0].is_empty() {
        anyhow::bail!("key does not have a database header file name");
    }
    Ok((parts[1], parts[0]))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_database_header_key_should_split_database_header_key_with_base_path_of_one_level_deep() {
        let input = "base_path/database_header_file_name.binpb";
        let (base_path, file_name) = split_database_header_key(input).unwrap();
        assert_eq!(base_path, "base_path");
        assert_eq!(file_name, "database_header_file_name.binpb");
    }

    #[test]
    fn split_database_header_key_should_split_database_header_key_with_base_path_of_two_level_deep() {
        let input = "level-1/level-2/deep_database_header_file_name.binpb";
        let (base_path, file_name) = split_database_header_key(input).unwrap();
        assert_eq!(base_path, "level-1/level-2");
        assert_eq!(file_name, "deep_database_header_file_name.binpb");
    }

    #[test]
    fn split_database_header_key_should_fail_if_key_does_not_include_slash() {
        let input = "database_header_file_name.binpb";
        assert!(split_database_header_key(input).is_err());
    }

    #[test]
    fn split_database_header_key_should_fail_if_base_path_is_empty() {
        let input = "/database_header_file_name.binpb";
        assert!(split_database_header_key(input).is_err());
    }

    #[test]
    fn split_database_header_key_should_fail_if_database_header_file_name_is_empty() {
        let input = "base_path/";
        assert!(split_database_header_key(input).is_err());
    }
}
