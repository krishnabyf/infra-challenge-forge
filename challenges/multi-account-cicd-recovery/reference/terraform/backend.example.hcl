bucket         = "payments-terraform-state-111122223333"
key            = "delivery/platform.tfstate"
region         = "us-east-1"
encrypt        = true
kms_key_id     = "arn:aws:kms:us-east-1:111122223333:key/replace-me"
dynamodb_table = "payments-terraform-locks"

