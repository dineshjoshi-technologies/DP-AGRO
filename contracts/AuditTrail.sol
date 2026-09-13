// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AuditTrail
/// @notice Immutable, append-only audit trail for the AI-Agriculture metrics pipeline.
/// @dev Implements the interface agreed in DPA-84#document-metrics-audit-trail-spec s2.2
///      and the event schema in dpa-182-spec/smart_contract_integration_spec.md s1.
///      Events form a hash-linked chain (eventId -> prevEventRef) so any dropped or
///      reordered record is detectable off-chain by recomputing the chain.
contract AuditTrail {
    // -------------------------------------------------------------------------
    // Types / state
    // -------------------------------------------------------------------------

    enum EventType {
        SENSOR_BATCH_INGEST,
        MODEL_TRAINING,
        MODEL_PROMOTION,
        PREDICTION_BATCH
    }

    struct AuditEvent {
        bytes32 eventId;
        uint256 timestamp;
        EventType eventType;
        address actor;
        bytes32 payloadHash;
        bytes32 prevEventRef;
    }

    /// @notice Contract owner: can grant/revoke recorders and upgrade schema version.
    address public owner;
    /// @notice Current schema version, bumped by recordSchemaVersion().
    uint256 public schemaVersion;
    /// @notice Recorders authorised to append audit events.
    mapping(address => bool) public recorders;
    /// @notice eventId => audit event.
    mapping(bytes32 => AuditEvent) public events;
    /// @notice payload hash => most recent eventId that recorded it (schema compliance lookup).
    mapping(bytes32 => bytes32) public payloadHashToEventId;
    /// @notice Highest eventId in the chain (head of the hash-linked ledger).
    bytes32 public latestEventId;
    /// @notice Total events appended.
    uint256 public eventCount;
    /// @notice Block number at which each event was mined.
    mapping(bytes32 => uint256) public eventBlock;

    // -------------------------------------------------------------------------
    // Events
    // -------------------------------------------------------------------------

    event AuditEventLogged(
        bytes32 indexed eventId,
        EventType indexed eventType,
        uint256 timestamp,
        address indexed actor,
        bytes32 payloadHash,
        bytes32 prevEventRef,
        uint256 blockNumber
    );
    event RecorderUpdated(address indexed recorder, bool allowed);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event SchemaVersionBumped(uint256 previousVersion, uint256 newVersion);

    // -------------------------------------------------------------------------
    // Modifiers
    // -------------------------------------------------------------------------

    modifier onlyOwner() {
        require(msg.sender == owner, "AuditTrail: not owner");
        _;
    }

    modifier onlyRecorder() {
        require(recorders[msg.sender], "AuditTrail: not a recorder");
        _;
    }

    constructor(address initialOwner) {
        require(initialOwner != address(0), "AuditTrail: invalid owner");
        owner = initialOwner;
        recorders[initialOwner] = true;
        schemaVersion = 1;
    }

    // -------------------------------------------------------------------------
    // Admin
    // -------------------------------------------------------------------------

    /// @notice Grant or revoke recorder permission for an ETL actor address.
    function setRecorder(address recorder, bool allowed) external onlyOwner {
        require(recorder != address(0), "AuditTrail: invalid recorder");
        recorders[recorder] = allowed;
        emit RecorderUpdated(recorder, allowed);
    }

    /// @notice Bump schema version when the governance policy defines a new revision.
    function recordSchemaVersion(uint256 newVersion) external onlyOwner {
        require(newVersion > schemaVersion, "AuditTrail: version not greater");
        uint256 previous = schemaVersion;
        schemaVersion = newVersion;
        emit SchemaVersionBumped(previous, newVersion);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AuditTrail: invalid new owner");
        address previousOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(previousOwner, newOwner);
    }

    // -------------------------------------------------------------------------
    // Append operations (interface from DPA-84 s2.2)
    // -------------------------------------------------------------------------

    /// @notice Log a sensor batch ingest hash for a farm.
    function logSensorBatch(bytes32 hash, uint256 timestamp, bytes32 farmId) external onlyRecorder {
        _append(
            EventType.SENSOR_BATCH_INGEST,
            keccak256(abi.encodePacked("sensor_batch_ingest", hash, timestamp, farmId)),
            timestamp,
            hash
        );
    }

    /// @notice Log a model training run (config + dataset hashes, metrics blob).
    function logModelTraining(
        bytes32 configHash,
        bytes32 datasetHash,
        bytes memory metrics
    ) external onlyRecorder {
        _append(
            EventType.MODEL_TRAINING,
            keccak256(abi.encodePacked("model_training", configHash, datasetHash, metrics)),
            block.timestamp,
            keccak256(abi.encodePacked(configHash, datasetHash, metrics))
        );
    }

    /// @notice Log a model promotion (staging -> prod).
    function logModelPromotion(address modelAddr, bytes32 version) external onlyRecorder {
        _append(
            EventType.MODEL_PROMOTION,
            keccak256(abi.encodePacked("model_promotion", modelAddr, version)),
            block.timestamp,
            keccak256(abi.encodePacked(modelAddr, version))
        );
    }

    /// @notice Log a prediction batch via merkle root (gas-efficient batching).
    function logPredictions(bytes32 merkleRoot, uint256 count) external onlyRecorder {
        _append(
            EventType.PREDICTION_BATCH,
            keccak256(abi.encodePacked("prediction_batch", merkleRoot, count)),
            block.timestamp,
            keccak256(abi.encodePacked(merkleRoot, count))
        );
    }

    /// @notice Returns true when the payload hash was recorded and its event is
    ///         linked into an intact chain (the event exists and its predecessor
    ///         is either the head-of-chain root or another recorded event).
    /// @dev Schema compliance: hash != 0x0 and prevEventRef is consistent with the ledger.
    function verifySchemaCompliance(bytes32 hash) external view returns (bool) {
        if (hash == bytes32(0)) return false;
        bytes32 eventId = payloadHashToEventId[hash];
        if (eventId == bytes32(0)) return false;
        AuditEvent storage e = events[eventId];
        if (e.eventId != eventId) return false;
        if (e.prevEventRef != bytes32(0) && events[e.prevEventRef].eventId != e.prevEventRef) {
            return false;
        }
        return true;
    }

    // -------------------------------------------------------------------------
    // Read helpers
    // -------------------------------------------------------------------------

    /// @notice Return a full event given its eventId.
    function getEvent(bytes32 eventId) external view returns (AuditEvent memory) {
        return events[eventId];
    }

    /// @notice Return the audit chain head. Client fetches latestEventId then walks prevEventRef.
    function head() external view returns (bytes32, uint256, bytes32) {
        return (latestEventId, eventBlock[latestEventId], events[latestEventId].prevEventRef);
    }

    // -------------------------------------------------------------------------
    // Internal
    // -------------------------------------------------------------------------

    function _append(EventType eventType, bytes32 eventId, uint256 timestamp, bytes32 payloadHash) internal {
        require(eventId != bytes32(0), "AuditTrail: zero eventId");
        require(payloadHash != bytes32(0), "AuditTrail: zero payloadHash");
        require(events[eventId].eventId == bytes32(0), "AuditTrail: duplicate eventId");

        AuditEvent storage e = events[eventId];
        e.eventId = eventId;
        e.timestamp = timestamp;
        e.eventType = eventType;
        e.actor = msg.sender;
        e.payloadHash = payloadHash;
        e.prevEventRef = latestEventId;
        eventBlock[eventId] = block.number;
        latestEventId = eventId;
        eventCount += 1;
        payloadHashToEventId[payloadHash] = eventId;

        emit AuditEventLogged(eventId, eventType, timestamp, msg.sender, payloadHash, e.prevEventRef, block.number);
    }
}