
# Security group for PostgreSQL
resource "aws_security_group" "postgres" {

  name        = "${var.db_name}-sg"
  description = "Allow PostgreSQL access from the backend Lambda"
  vpc_id      = var.vpc_id

  # Inbound traffic
  ingress {
    description = "PostgreSQL from backend Lambda"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.network_cidr_block]
  }

  # Allow outbound traffic for database operations
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "postgres" {
  name       = "${var.db_name}-subnets"
  subnet_ids = var.private_subnets
}

# PostgreSQL database
resource "aws_db_instance" "postgres" {
  identifier = var.db_name

  engine         = "postgres"
  instance_class = var.db_instance_class

  db_name  = "wf_detection"
  username = "dbadmin"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  publicly_accessible    = false

  multi_az                   = false
  backup_retention_period    = 1
  auto_minor_version_upgrade = true

  deletion_protection       = false
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.db_name}-final"
}
