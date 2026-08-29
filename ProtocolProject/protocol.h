#ifndef CHANGE_CASE_PROTOCOL_H
#define CHANGE_CASE_PROTOCOL_H

#include <string>
#include <stdexcept>
#include <cstddef>

namespace ChangeCaseProtocol
{
    // Protocol constants
    constexpr std::size_t MAX_TEXT_LENGTH = 1024 * 1024; // 1 MiB
    constexpr std::size_t LENGTH_DIGITS = 7;

    constexpr const char* CRLF = "\r\n";

    // Message types
    enum class MessageType
    {
        REQ,
        ANS
    };

    // Operations
    enum class Operation
    {
        LWR,
        UPR
    };

    // Parsed message
    struct Message
    {
        MessageType type;
        Operation operation;
        std::string text;
    };

    // Convert MessageType to string
    inline std::string typeToString(MessageType type)
    {
        switch (type)
        {
            case MessageType::REQ:
                return "REQ";

            case MessageType::ANS:
                return "ANS";
        }

        throw std::runtime_error("Invalid message type");
    }

    // Convert Operation to string
    inline std::string operationToString(Operation operation)
    {
        switch (operation)
        {
            case Operation::LWR:
                return "LWR";

            case Operation::UPR:
                return "UPR";
        }

        throw std::runtime_error("Invalid operation");
    }

    // -----------------------------
    // Build protocol message
    //
    // Example:
    //
    // REQ\r\n
    // UPR\r\n
    // LEN=0000005\r\n
    // Hello
    // -----------------------------

    inline std::string buildMessage(
        MessageType type,
        Operation operation,
        const std::string& text
    )
    {
        // Check maximum payload size
        if (text.size() > MAX_TEXT_LENGTH)
        {
            throw std::runtime_error("Text exceeds maximum payload size");
        }

        // 7 digits can represent up to 9,999,999
        if (text.size() > 9999999)
        {
            throw std::runtime_error("Text is too large for LEN field");
        }

        // Convert length to a 7-digit string
        std::string length = std::to_string(text.size());

        length = std::string(LENGTH_DIGITS - length.size(),'0') + length;


        return typeToString(type) + CRLF
             + operationToString(operation) + CRLF
             + "LEN=" + length + CRLF
             + text;
    }


    // -----------------------------
    // Parse protocol message
    // -----------------------------

    inline Message parseMessage(const std::string& data)
    {
        const std::string delimiter = CRLF;

        // -------------------------
        // Parse message type
        // -------------------------

        std::size_t pos1 = data.find(delimiter);

        if (pos1 == std::string::npos)
        {
            throw std::runtime_error("Invalid message: missing message type");
        }

        std::string typeStr =
            data.substr(0, pos1);


        // -------------------------
        // Parse operation
        // -------------------------

        std::size_t pos2 =
            data.find(delimiter, pos1 + delimiter.size());

        if (pos2 == std::string::npos)
        {
            throw std::runtime_error("Invalid message: missing operation");
        }

        std::string operationStr =
            data.substr(pos1 + delimiter.size(),pos2 - (pos1 + delimiter.size()));

        // Parse LEN
        std::size_t pos3 =
            data.find(delimiter, pos2 + delimiter.size());

        if (pos3 == std::string::npos)
        {
            throw std::runtime_error("Invalid message: missing length");
        }

        std::string lengthField =data.substr(pos2 + delimiter.size(),pos3 - (pos2 + delimiter.size()));


        // Must start with "LEN="
        if (lengthField.size() != 4 + LENGTH_DIGITS || lengthField.substr(0, 4) != "LEN=")
        {
            throw std::runtime_error("Invalid LEN field");
        }


        // -------------------------
        // Validate length digits
        // -------------------------

        std::string lengthString = lengthField.substr(4);

        for (char c : lengthString)
        {
            if (c < '0' || c > '9')
            {
                throw std::runtime_error("Invalid length value");
            }
        }


        // Convert length
        std::size_t length = std::stoul(lengthString);


        // Maximum length
        if (length > MAX_TEXT_LENGTH)
        {
            throw std::runtime_error("Payload exceeds maximum size");
        }


        // -------------------------
        // Locate payload
        // -------------------------

        std::size_t payloadStart = pos3 + delimiter.size();


        // Check that enough data exists
        if (data.size() - payloadStart < length)
        {
            throw std::runtime_error("Incomplete payload");
        }


        // Extract exactly LEN bytes
        std::string text = data.substr(payloadStart, length);


        // -------------------------
        // Convert message type
        // -------------------------

        MessageType type;

        if (typeStr == "REQ")
        {
            type = MessageType::REQ;
        }
        else if (typeStr == "ANS")
        {
            type = MessageType::ANS;
        }
        else
        {
            throw std::runtime_error("Invalid message type");
        }

        // -------------------------
        // Convert operation
        // -------------------------

        Operation operation;

        if (operationStr == "LWR")
        {
            operation = Operation::LWR;
        }
        else if (operationStr == "UPR")
        {
            operation = Operation::UPR;
        }
        else
        {
            throw std::runtime_error("Invalid operation");
        }


        // -------------------------
        // Return parsed message
        // -------------------------

        return { type, operation, text };
    }

}

#endif