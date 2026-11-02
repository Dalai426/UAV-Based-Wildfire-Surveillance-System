

```bash
 aws login --profile ce1-group-ds
 AWS Region [us-east-1]: eu-north-1
```
### Creating Tunnel to the DB from Local using Bastion
```bash
ssh -i ~/.ssh/aws-bastion -N -L 5432:drone-surveillance-system-eu-north-1-db.cfog8cc8ilss.eu-north-1.rds.amazonaws.com:5432 ec2-user@13.62.222.219
```
### Showing The State of Infrastructure
terraform show
terraform show | grep -A 20 "aws_security_group"
### Getting generated outputs
```bash
terraform output
```
### Mutual TLS between Ground Stations and the AWS IoT core.

```bash
curl \
  --cert certificate.pem.crt \
  --key private.pem.key https://c1ve6zt4i027sy.credentials.iot.eu-north-1.amazonaws.com/role-aliases/GSRoleAlias/credentials
```
In Mutual TLS, both sides in communication need to have own pub/priv keys, own identity certificate, and CA Certificate from a CA (Certificate Authority).
**certificate.pem.crt** - Both sides need to obtain an X.509 certificate, which contains the device's public key and the signature of device identity signed by the CA's private key, from the CA.
**AmazonRootCA1.pem** - the CA certificate is a trusted certificate from the Certificate Authority (Amazon's Default CA), containing the CA's public key and identity information. It is used for verifying the identity certificate sent from the opposite handshaking  part. Our computer's operating system can store all useful CA certificates

#### The Mutual TLS connection is established according to the below way:
1. The GS initiates connection, sending information such as supported TLS versions and cipher suites.
2. The AWS IoT core sends its server certificate containing its public key and the digital signature signed by the CA.
3. The GS uses its trusted CA certificate to verify the server's certificate from the AWS IoT core.
4. The GS sends its certificate (certificate.pem.crt) to the AwS IoT core
5. The server verifies the certificate using the public key in the CA certificate obtained from the CA.
6. Both sides send data to each other, signed by their private key. The receiving party verify data using the sending party's certificate.