resource "random_string" "omnipotence" {
  length  = 4
  special = false
  number  = false
  upper   = false
}

# We can remove this process after ConsoleMe is open sourced
resource "aws_s3_bucket" "consoleme_source_bucket" {
  bucket = "${lower(var.bucket_name_prefix)}-${random_string.omnipotence.result}"
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  force_destroy = true
  tags          = merge(map("Name", var.bucket_name_prefix), var.default_tags)
}


resource "aws_s3_bucket_object" "consoleme_zip" {
  bucket = aws_s3_bucket.consoleme_source_bucket.bucket
  key    = "consoleme.tar.gz"

  source  = "${path.module}/../../consoleme.tar.gz"

  etag    = md5(filebase64("${path.module}/../../consoleme.tar.gz"))
}