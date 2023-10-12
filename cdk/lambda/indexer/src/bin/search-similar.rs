//! `search-similar`
//!
//! You have to configure the following environment variables:
//! - `DATABASE_BUCKET_NAME`: name of the S3 bucket that stores the database
//!   files.
//! - `DATABASE_HEADER_KEY`: object key of the database header file in the S3
//!   bucket for the database.
//!
//! The function accepts an array of 1,536 `f32` values compatible with
//! [OpenAI's embedding model "text-embedding-ada-002"](https://platform.openai.com/docs/models/embeddings)
//! and returns an array of [`SimilarMumbling`]s.

use anyhow::{anyhow, bail};
use flechasdb::db::AttributeValue;
use flechasdb::asyncdb::stored::{Database, LoadDatabase};
use flechasdb_s3::asyncfs::S3FileSystem;
use futures::future::try_join_all;
use lambda_runtime::{Error, LambdaEvent, run, service_fn};
use serde::Serialize;
use std::env;

use indexer::utils::split_database_header_key;

/// Link to a mumbling in search results.
#[derive(Serialize)]
pub struct SimilarMumbling {
    /// ID (URL) of the mumbling fragment.
    id: String,
    /// Approximate squared distance.
    distance: f32,
}

async fn function_handler(
    event: LambdaEvent<Vec<f32>>,
) -> Result<Vec<SimilarMumbling>, Error> {
    const K: usize = 30;
    const NPROBE: usize = 1;
    let database_bucket_name = env::var("DATABASE_BUCKET_NAME")?;
    let database_header_key = env::var("DATABASE_HEADER_KEY")?;
    let config = aws_config::load_from_env().await;
    let (base_path, header_path) =
        split_database_header_key(&database_header_key)?;
    let db: Database<f32, _> = Database::load_database(
        S3FileSystem::new(&config, database_bucket_name, base_path),
        header_path,
    ).await?;
    let results = db.query(
        &event.payload,
        K.try_into().unwrap(),
        NPROBE.try_into().unwrap(),
    ).await?;
    let results = try_join_all(results.into_iter().map(|r| async move {
        r.get_attribute("content_id").await?
            .ok_or(anyhow!("content_id is not assigned"))
            .and_then(|value| if let AttributeValue::String(id) = value {
                Ok(SimilarMumbling {
                    id,
                    distance: r.squared_distance,
                })
            } else {
                bail!("content_id is not a string")
            })
    })).await?;
    Ok(results)
}

#[tokio::main]
async fn main() -> Result<(), Error> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        // disable printing the name of the module in every log line.
        .with_target(false)
        // disabling time is handy because CloudWatch will add the ingestion time.
        .without_time()
        .init();

    run(service_fn(function_handler)).await
}
