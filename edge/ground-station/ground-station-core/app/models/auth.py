from pydantic import BaseModel, Field


class HandshakeInitRequest(BaseModel):
    drone_id: str
    nonce_drone: str
    drone_certificate: str


class HandshakeInitResponse(BaseModel):
    handshake_id: str
    nonce_gs: str
    encrypted_pms: str
    signature: str
    ground_station_certificate: str


class HandshakeCompleteRequest(BaseModel):
    handshake_id: str
    confirmation: str
